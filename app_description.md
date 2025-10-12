I want to make a typing app specifically for developers to improve their typing speed. Also I want to make it in python so that it can be run anywhere and I also want to be able to build a executable for windows and Linux so that general public can just use it by installing it and have nothing else to worry about.

So I want to build it with python. I want uv to manage it. Like uv init uv add uv run etc

Now for the app. It should be totally offline and work with local codebase provided by the user. The only time internet may be required is for downloading icons and stuff like that.

Here is what I envision it to be. I app first build in dark mode specifically Nord theme. Obviously users can change it from settings. if the choose light mode they are for now stuck with generic light theme. I don't like light them. For dark theme they can choose from these color schemes: Nord, Catpucchin, Dracula

Now lets get to the ui. The ui should be modern minimalistic. There should be 4 tabs in the main window. The folders tab, the languages tab, the settings tab, and the typing tab.

Folders tab:
The Folders tab will look enitially empty. It will have a plus icon. When the user clicks this icon a window opens up from which users can select folders from their pc. They can add as many folders as they want. The folders tab after adding the folders will look like windows file explorer with big icon view this can also be changed to detail view and yes this is like windows one. There will be a pencil icon too. Clicking this will make a red cross appear on each of the folders. Clicking the cross will prompt a dilogue box if the user is sure they want to remove the folder. There will also be a check box like don't ask again. if they check this box this dilogue will not appear from the next time. This can be changed from the settings tab.
clicking on the folders take user to editor/typing tab. 
The folders the users add basically contain different types of files they can type like .txt, .c .cpp .py etc



Languages tab:
the view will be similar to folder view here there will be cards with diffrent programming languages name like python c cpp java etc. The folders will have the languages icon and also the name will be shown in legend below. basically what these will contain are filtered files like when the folders are added they may contain various types of files in each of them like c python java etc this tab filters them to their own containers. So basically here is what will happen. Say if there is python card it will contain all .py files found accross all folders added by the user. The card will have python logo/icon there will be also total files count. it will be shown like this 5/76 basically 76 is the total amount of .py fils across all folders. and 5 will be the number of .py files which has been fully typed and practiced on. It will also have AVG WPM which shows the average speed for this language. This will be calculated by taking the average of the last 15 .py files typing speed. or if tehre is a better way to calculate this that. clicking on any of the cards will aslo take you to the editor/typing tab. The icons or logos shown here will have to be downloaded this is the part that will require internet if icons are not already present. The cards are automatically generated. Like if there is no c files in any of the folders user added then there will be no card for c but as soon as a folder is added that has c then a c card will be created. The language icons are supposed to be automatically downloaded dynamically. when new files are detected and they should be stored in an appropriate location. as to not require internet every time.

editor/typing tab:
editor tab will be devided into 2 parts the left part being smaller than the right one. The left one will show the file tree the right part will show typing area. the right part will be then vertically devided into two parts. The top part will have more space and this is where the contents of files be shown and here typing will be done. The lower part will be dedicated to stats. Like live wpm count, time, accuracy, total keystrokes count etc.


now the file tree. If this editor/typing tab is arrived by clicking on the folders from the folders tab then it will just show the file tree like normal like it would be in vs code. Clicking on any file like say x.py will show the content in the typing area. If this tab was arrived from the languages tab then there will be all folders listed like say the user has added folder p q r s and p q r has .py files in them while s doesn't if typing tab is arrived by typing the python card on the language tab. then the file tree will show p q r folders in collapsed mode the user can expand them and choose files from them. In the file tree besides folder and files name there will be two columns One called best and one called last. These two columns will show for each file the best wpm achieved on that file ever as well as the las wpm achieved on it. oh the file tree will also have icons associated with files like vs code does.


the typing  area:
when a file is clicked its content will be shown on the typing area. when it is initially loaded the content as in the text will be greyish or grey dark as in these haven't been typed yet. When the user starts typing they will change color. Green for correct red for incorrect. Also say the character to type is 'c' but user types x then this x will be shown in red inplace of c. This behavior can be changed from the settings tab from the option show what was typed. if true it will show x in red if false it will show c in red. also there is also another thing the space character in the file in the typing are will be shown as ␣ by default. By that i mean say the text is "hi there" it will show "hi␣there" by default. when the cursor reaches ␣ it will also be treated like any other character so it shouldn't just disappear when the cursor reaches it. Also is say i was to type 'p' but typed ␣ instead it should show ␣ in read in place of p. also enter should be shown as ⏎ and it should be treated the same way as space. Now the space bar part this should be changeble from the settings tab like it could be instead shown as . or as it would be normally shown ' ' or a custom one defined by user. backspace will work like it should it will delete typed character. The file content should never change format like say i am at the end of a line and instead of pressing enter i press something else then the line below should not come up it should stay where it is. and if i press x instead of enter then x should appear as red and then the cursor should go to the next line. Speaking of cursor the cursor type style color can also be changed from the settings tab as well as the color for untyped text, correctly typed and incorrectly typed text. Now the tab button should also work like it should. it should eneter 4 spaces. like user should not be expected to manually enter 4 or more spaces that is unreasonable. So tab button should enter 4 spaces. Here one thing to reember tab generaly shifts elements. like say in a log in form in the username box if you press enter it will take you to the next box like password. But this funcitonality of tab should not exist in this app because it could and will conflict with entering 4 spaces. Then also control backspace should also be implemented. Like it should do what it does in any text like it should do what it does in vs code. deletes the word to the left of the cursor. Then another thing say for some reason the user has to move away from the keyboard while they were typing now if the time still counts on then their wpm will drop and that isn't what we want. So if any keystroke hasn't been detected in the last 7 seconds then pause the session meaning their clock will not go forward it will remain paused until the user doesn't enter another keystroke. As soon as the user enters another keystroke unpause and continue like before. This time delay can also be changed from the settings tab. By default it is 7s . Another thing, say the user is practicing on a 1000 lines .py file they won't obviously finish it in one sittng. so say they reach line 97 then they press the cross button on the window. What should happen is the position should be remembered it should be paused. like next time the application is launched and user opens this file then the cursor should be still on that 97th line and the session should be paused. when the user enters a keystroke it should unpause and user should be able to carry on from the 97th line onwards. This should be done for multiple files like if the user doesn't resume with the file they were last typing instead starts another long file and doesn't finish that either that files last location should also be saved as in the next time the user can choose either of the files and continue from where they left off. These types of files shoudl be marked in yellowish highlight in the editor veiw to indicate that you were once typing these but you didn't finish. obviously this yellowish color is also change able from the settings tab. in the typing area around the top right there should be a revert cursor the top of file button. this is for the cases like you have closed the app when you were typing and the app reembers the location but its been a long time so you wish to start from the beginning this will set the cursor position back to the beginning of the file and the stats part below shall also be reset. Another thing seek to cursor should be enabled as to if the cursor goes out of sight when the content is too houge the focus is automatically gone to the are where the cursor is so that the user can actually see what is it that they are typing. The font family the font size can also be changed from the setting.



The stats area:
it should show the wpm in green the time in silver the accuracy in green, detailed kestrokes info too.
it should be like these there will be 4 columns one column for wpm one for time one for accuracy and one for keystrokes. The keystrokes column or box should have a top and a bottom part. each part will show 3 information correct wrong and total keystrokes the top one should show the actual count the bottom one should show the percentage. The correct should be in green text incorrect in red and total in light blue.

This part should also show a paused indication when it is paused. 









settings:
deletion dilogue box hide true false
option to choose light or dark theme
if dark theme is chosen then select color scheme from dracula, nord, catpuccin 
files to ignore box users can add file extensions like .pdf .png etc
folders to ignore box users can add folders like .venv or any other that make sense they 
these two boxes will be prefilled with some sensible entries by default which obviously users can change.
space character shown as : by default the options will be . ' ' ␣ or custom. if custom is selected user can enter their custom character like say $ or any other character.
cursor type: blinking or static
cursor style: block underscore ibeam and any othe popular ones
cursor color:
untyped text color:
correctly typed text color:
incorrectly typed text color:
paused files highlight color: yellowish by default change able by user.
These color can be chosen by the user from a color wheel as well as by enetering color hex values. Besides each of these colors there should be a revert to default button. 
pause delay: 7s chanable by user.
font family:
font size:
font ligatures:
export settings as json
import settings from json
export data
import data

the export and import features are for backup purposes. As to if the user changes pc they can take their data with them. Settings cahnges should persist through app close and open. Like say i change some settings then i close the app when i relaunch the app the settings changes should not be undone as in they should not revert to default.



this app should be made in such a way that it can be run as just python files like uv run main.py or i should be able to build a binary from it like .exe for windows .deb for anything similar for linux and the exe and .deb should be such that i can just do a github release and non technical people just download it and use it. it would be best to make it a portable installer. as not not really needing to be installed if possible. 