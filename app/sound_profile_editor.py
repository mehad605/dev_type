"""Dialog for creating and editing custom sound profiles - simplified for keypress only."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from pathlib import Path
from typing import Optional


class SoundProfileEditor(QDialog):
    """Dialog for creating/editing custom sound profiles."""
    
    def __init__(self, profile_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.profile_id = profile_id
        self.is_new = profile_id is None
        
        self.setWindowTitle("Create Custom Sound" if self.is_new else "Edit Sound")
        self.setMinimumWidth(500)
        
        self._setup_ui()
        
        if not self.is_new:
            self._load_profile_data()
    
    def _setup_ui(self):
        """Setup the UI elements."""
        layout = QVBoxLayout(self)
        
        # Sound Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Sound Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Custom Keyboard")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Profile ID is auto-generated, no need to show it to user anymore
        
        # Sound file group
        sounds_group = QGroupBox("Keypress Sound")
        sounds_layout = QHBoxLayout()
        
        self.sound_path = QLineEdit()
        self.sound_path.setReadOnly(True)
        self.sound_path.setPlaceholderText("No file selected")
        sounds_layout.addWidget(self.sound_path)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_sound)
        sounds_layout.addWidget(browse_btn)
        
        test_btn = QPushButton("🔊 Test")
        test_btn.clicked.connect(self._test_sound)
        sounds_layout.addWidget(test_btn)
        
        sounds_group.setLayout(sounds_layout)
        layout.addWidget(sounds_group)
        
        # Info label
        info = QLabel("💡 Tip: Use .wav files for zero-latency typing feedback.")
        info.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(info)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Sound")
        save_btn.clicked.connect(self._save_profile)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _browse_sound(self):
        """Browse for a sound file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Keypress Sound",
            "",
            "WAV Audio (*.wav);;All Files (*.*)"
        )
        
        if file_path:
            if not file_path.lower().endswith(".wav"):
                QMessageBox.warning(self, "Unsupported Format", "Only .wav files are supported for typing sounds to ensure low latency.")
                return
            self.sound_path.setText(file_path)
    
    def _test_sound(self):
        """Test play the sound file."""
        from PySide6.QtMultimedia import QSoundEffect
        from PySide6.QtCore import QUrl
        
        file_path = self.sound_path.text()
        
        if not file_path or not Path(file_path).exists():
            QMessageBox.warning(self, "No File", "Please select a sound file first.")
            return
        
        # Play the sound
        # Play the sound using QMediaPlayer for better format support
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        
        self.test_player = QMediaPlayer()
        self.test_audio_output = QAudioOutput()
        self.test_player.setAudioOutput(self.test_audio_output)
        self.test_audio_output.setVolume(1.0)
        
        self.test_player.setSource(QUrl.fromLocalFile(file_path))
        self.test_player.play()
    
    def _load_profile_data(self):
        """Load existing profile data for editing."""
        from app.sound_manager import get_sound_manager
        manager = get_sound_manager()
        
        all_profiles = manager.get_all_profiles()
        if self.profile_id not in all_profiles:
            return
        
        profile = all_profiles[self.profile_id]
        self.name_edit.setText(profile["name"])
        
        # Load file path
        sound_file = manager.get_profile_sound_file(self.profile_id)
        if sound_file:
            self.sound_path.setText(sound_file)
    
    def _save_profile(self):
        """Save the profile."""
        from app.sound_manager import get_sound_manager
        import re
        
        # Validate
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a profile name.")
            return
        
        if self.is_new:
            # Auto-generate profile ID from name
            # Convert to lowercase, replace spaces/special chars with underscores
            profile_id = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
            
            if not profile_id:
                QMessageBox.warning(self, "Invalid Name", "Please enter a valid profile name with at least one alphanumeric character.")
                return
            
            # Check if ID already exists
            manager = get_sound_manager()
            if profile_id in manager.get_all_profiles():
                # Add a number suffix to make it unique
                counter = 1
                base_id = profile_id
                while f"{base_id}_{counter}" in manager.get_all_profiles():
                    counter += 1
                profile_id = f"{base_id}_{counter}"
        else:
            profile_id = self.profile_id
        
        sound_file = self.sound_path.text()
        if not sound_file or not Path(sound_file).exists():
            QMessageBox.warning(self, "Missing Sound", "Please select a sound file.")
            return
        
        if not sound_file.lower().endswith(".wav"):
            QMessageBox.warning(self, "Invalid Format", "Only .wav files are supported.")
            return
        
        # Create/update profile
        manager = get_sound_manager()
        
        if self.is_new:
            success = manager.create_custom_profile(profile_id, name, sound_file)
            if success:
                QMessageBox.information(self, "Success", f"Sound '{name}' created successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to create sound.")
        else:
            success = manager.update_custom_profile(profile_id, sound_file=sound_file, name=name)
            if success:
                QMessageBox.information(self, "Success", f"Sound '{name}' updated successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update sound.")
