## Hands-On: Python Concepts for Async Agent Execution

This section covers essential Python concepts you need to understand how async agent execution works.

### Python Concepts Recap

#### Iterators

An **iterator** is an object that produces values one at a time when you loop over it. Any object that implements the iterator protocol (`__iter__()` and `__next__()` methods) is an iterator. Lists, tuples, and strings are all iterable.

```python
numbers = [1, 2, 3]
iterator = iter(numbers)
print(next(iterator))  # 1
print(next(iterator))  # 2
print(next(iterator))  # 3

# Or use a for loop, which calls next() automatically
for num in numbers:
    print(num)
```

The key concept: an iterator provides a uniform way to access elements sequentially without exposing the underlying structure.

#### Generators

A **generator** is a special type of iterator created in two ways: using a function with the `yield` keyword, or using a generator expression (similar to list comprehensions but with parentheses).

**Generator function:**
```python
def count_up_to(n):
    i = 0
    while i < n:
        yield i
        i += 1

for num in count_up_to(3):
    print(num)  # Prints: 0, 1, 2
```

When you call a generator function, it returns a generator object but doesn't execute the function body yet. Each time you iterate, Python executes the function until it hits `yield`, pauses, returns the value, and resumes on the next iteration.

**Generator expression:**
```python
# List comprehension - creates entire list in memory
squares_list = [x * x for x in range(5)]  # [0, 1, 4, 9, 16]

# Generator expression - uses parentheses, lazy evaluation
squares_gen = (x * x for x in range(5))

for square in squares_gen:
    print(square)  # Prints: 0, 1, 4, 9, 16
```

Generator expressions use parentheses `()` instead of square brackets `[]`. Unlike list comprehensions that build the entire list in memory, generator expressions compute values on demand as you iterate over them.

The key advantage: generators produce values lazily, one at a time, without loading everything into memory. This is perfect for processing streams of data or events.

#### Context Managers

A **context manager** handles resource setup and cleanup automatically using the `with` statement. It guarantees cleanup happens even if errors occur.

```python
with open('file.txt', 'r') as f:
    data = f.read()
# File is automatically closed here, even if an error occurred
```

You create context managers in two ways:

**Using a class with `__enter__()` and `__exit__()` methods:**
```python
class DatabaseConnection:
    def __enter__(self):
        self.connection = connect_to_db()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()
        return False  # Don't suppress exceptions

with DatabaseConnection() as conn:
    conn.execute("SELECT * FROM users")
# Connection is automatically closed
```

**Using the `@contextmanager` decorator (with a generator):**
```python
from contextlib import contextmanager

@contextmanager
def database_connection():
    conn = connect_to_db()  # Setup before yield
    try:
        yield conn  # Yield the resource
    finally:
        conn.close()  # Cleanup after yield

with database_connection() as conn:
    conn.execute("SELECT * FROM users")
# Connection is automatically closed
```

This approach uses a generator function. The `@contextmanager` decorator converts it into a context manager: code before `yield` runs on entry, the yielded value becomes the `as` variable, and code after `yield` (in the `finally` block) runs on exit.

The cleanup in `__exit__()` or the `finally` block always runs, making resource management safe and predictable.

#### Coroutines and Async/Await

A **coroutine** is a function defined with `async def` that can pause execution using `await` and let other coroutines run. This is **cooperative multitasking**: the coroutine voluntarily yields control when waiting for I/O operations like network requests, disk reads, database queries, or API calls.

```python
async def fetch_user_data(user_id):
    # When waiting for network response, this coroutine yields control
    response = await http_client.get(f"/users/{user_id}")

    # When waiting for disk I/O, it yields control again
    await file.write(response.content)

    return response.json()

async def main():
    # While waiting for fetch_user_data, other coroutines can run
    result = await fetch_user_data(123)
```

Each `await` is a point where the coroutine says "I'm waiting for something (network, disk, database), so let other coroutines run while I wait."

The difference from threads and processes:

**Cooperative multitasking (async/await)**: A single thread runs multiple coroutines. Each coroutine explicitly yields control with `await`. No true parallelism, but excellent for I/O-bound operations where you're waiting for network, disk, or API responses. Very lightweight and efficient.

**Preemptive multitasking (threads/processes)**: The operating system switches between threads/processes forcibly, allowing true parallel execution on multiple CPU cores. Better for CPU-intensive work but has overhead from context switching and requires careful synchronization.

For agent work involving API calls, async/await is ideal: you spend most time waiting for model responses, not doing heavy computation.

#### Async Iterators and Generators

An **async iterator** produces values asynchronously using `async for`. An **async generator** is a coroutine that uses `yield` to produce values one at a time, with each iteration possibly involving async operations.

```python
async def fetch_pages():
    for page in range(3):
        await asyncio.sleep(0.1)  # Simulate async I/O
        yield f"Page {page}"

async def main():
    async for page in fetch_pages():
        print(page)
```

This combines the benefits of generators (lazy, streaming evaluation) with async operations (efficient I/O handling).

#### Async Context Managers

An **async context manager** is like a regular context manager but for async operations. It uses `async with` and can perform async setup/cleanup.

```python
class AsyncResource:
    async def __aenter__(self):
        await self.connect()  # Async setup
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()  # Async cleanup

async def main():
    async with AsyncResource() as resource:
        await resource.do_work()
    # Cleanup guaranteed to happen
```

This is essential when resources require async operations to initialize or clean up, like network connections or database sessions.

### Summary

These Python concepts combine to enable efficient, streaming agent execution. 
