// Demo JavaScript file for testing
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(x => x * 2);

console.log("Fibonacci of 10:", fibonacci(10));
console.log("Doubled:", doubled);
