## Hands-On: Verification / Critique Pattern

The verification/critique pattern introduces explicit evaluation into an agent's workflow. Rather than trusting the first output, the agent (or a separate verifier) checks the result against defined criteria before accepting it. This hands-on explores the pattern using `example_verification_critique.ipynb`, demonstrating how explicit verification loops improve reliability for constraint-satisfaction tasks.

## Verification vs Self-Reflection

While self-reflection asks an agent to generally critique and improve its work, verification/critique is more focused: it checks outputs against explicit, enumerable criteria. The evaluation is structured rather than open-ended. A verifier answers specific questions like "Does this satisfy constraint X?" rather than "Is this good?"

This distinction matters in practice. Self-reflection works well when quality is somewhat subjective or when the agent needs to discover what might be wrong. Verification works well when you know exactly what "correct" means and can express it as checkable criteria.

## The Password Generation Example

The notebook uses password generation as its example because passwords have clear, verifiable constraints. A password either satisfies a rule or it doesn't. This makes the verification step unambiguous and easy to follow.

The constraints defined in the notebook are:

```python
CONSTRAINTS = """
1. Exactly 12 characters long
2. Contains at least 2 uppercase letters
3. Contains at least 2 lowercase letters
4. Contains at least 2 digits
5. Contains at least 2 special characters from: !@#$%^&*
6. No consecutive repeating characters (e.g., 'aa' or '11' is not allowed)
"""
```

Each constraint is precise and independently checkable. The verifier can evaluate them one by one and report exactly which ones pass or fail.

## Separate Generator and Verifier

The pattern uses two distinct agent roles rather than having one agent do everything.

```python
generator_system_prompt = """You are a password generator. Generate passwords that satisfy the given constraints.
Output ONLY the password, nothing else."""

generator = get_agent(system_prompt=generator_system_prompt)
```

The generator's job is focused: produce a password. It doesn't evaluate or explain.

```python
verifier_system_prompt = """You are a password validator. Given a password and constraints, check each constraint.

For each constraint, output:
- PASS: [constraint] - [brief explanation]
- FAIL: [constraint] - [brief explanation]

At the end, output a line:
VERDICT: ALL_PASS or VERDICT: SOME_FAIL

Be precise and check character by character if needed."""

verifier = get_agent(system_prompt=verifier_system_prompt)
```

The verifier's job is also focused: check each constraint and report results. The structured output format (PASS/FAIL per constraint, final VERDICT) makes it easy to parse the result programmatically.

This separation of concerns mirrors how verification works in other domains. A compiler doesn't write code; it checks code. A test suite doesn't implement features; it verifies them. Keeping generation and verification separate makes each role simpler and more reliable.

## The Verification Loop

The core of the pattern is a loop that continues until verification passes or a maximum iteration count is reached.

```python
async def generate_with_verification(constraints: str, max_iterations: int = MAX_ITERATIONS) -> tuple[str, int]:
    generator = get_agent(system_prompt=generator_system_prompt)
    verifier = get_agent(system_prompt=verifier_system_prompt)

    gen_prompt = f"Generate a password satisfying these constraints:\n{constraints}"
    gen_run, gen_nodes = await run_agent(generator, gen_prompt)
    password = gen_run.result.output.strip()

    for iteration in range(max_iterations):
        # Verify
        verify_prompt = f"Verify this password against the constraints:\n\nPassword: {password}\n\nConstraints:\n{constraints}"
        verify_run, _ = await run_agent(verifier, verify_prompt)
        verification = verify_run.result.output

        # Check verdict
        if "VERDICT: ALL_PASS" in verification:
            return password, iteration + 1

        # Regenerate with feedback
        message_history = nodes_to_message_history(gen_nodes)
        feedback_prompt = f"""The password '{password}' failed verification:

{verification}

Generate a new password that fixes the failed constraints. Output ONLY the password."""

        gen_run, gen_nodes = await run_agent(generator, feedback_prompt, message_history=message_history)
        password = gen_run.result.output.strip()

    return password, max_iterations
```

The loop has three phases in each iteration:

**Verify**: The verifier checks the current password against all constraints. The verification prompt includes both the password and the constraints, giving the verifier everything it needs.

**Check verdict**: The code looks for "VERDICT: ALL_PASS" in the verifier's output. This simple string check determines whether to accept the result or continue iterating.

**Regenerate with feedback**: If verification failed, the generator receives the full verification report showing which constraints failed. This is the critical difference from blind retry. The generator knows exactly what went wrong and can focus on fixing those specific issues.

## Feedback Through Message History

The regeneration step uses message history to maintain context:

```python
message_history = nodes_to_message_history(gen_nodes)
feedback_prompt = f"""The password '{password}' failed verification:

{verification}

Generate a new password that fixes the failed constraints. Output ONLY the password."""

gen_run, gen_nodes = await run_agent(generator, feedback_prompt, message_history=message_history)
```

The generator sees its previous attempt and the specific failures. This allows it to understand what it got wrong and adjust. Without message history, each generation attempt would be independent, potentially repeating the same mistakes.

## Why Separate Agents?

Using two agents (generator and verifier) rather than one agent that does both has several advantages.

Focused prompts are more reliable. A prompt that says "generate and then verify" asks the model to context-switch mid-response. Separate agents keep each task simple.

Independent verification is more trustworthy. When the same agent generates and verifies, there's a risk of confirmation bias: the agent may be more lenient when checking its own work. A separate verifier has no investment in the generated output.

The pattern scales to external verification. In production, the verifier might not be an LLM at all. It could be a deterministic function, a test suite, or a human reviewer. Separating the roles makes this substitution easy.

## Comparison: With and Without Verification

The notebook includes a comparison showing direct generation without a verification loop:

```python
direct_agent = get_agent(system_prompt="You generate passwords. Be very careful to satisfy all constraints exactly.")

direct_run, _ = await run_agent(direct_agent, f"""Generate a password satisfying ALL these constraints exactly:
{CONSTRAINTS}

Output only the password.""")

direct_password = direct_run.result.output.strip()
```

Adding "be very careful" to the prompt is hoping for correctness rather than checking for it. The model might still make mistakes, especially with tricky constraints like "no consecutive repeating characters" which require careful attention.

When the direct output is then verified, it may or may not pass all constraints. The verification loop ensures that failures are caught and corrected rather than silently delivered.

## When Verification Helps

The verification/critique pattern is most effective when correctness criteria are explicit and checkable, when a single generation attempt may not satisfy all constraints, when the cost of incorrect output is high, and when feedback can guide improvement.

Password generation is a clear example, but the pattern applies broadly. Code that must pass tests, configurations that must validate against a schema, documents that must include required sections, plans that must satisfy stated constraints: all of these benefit from explicit verification.

## When Verification Is Less Useful

Verification adds latency and cost. Each iteration requires at least two API calls (generate + verify). For tasks where the model reliably gets it right the first time, verification overhead isn't justified.

Verification also requires that you can express correctness criteria clearly. For subjective tasks like "write an engaging blog post," defining what the verifier should check becomes difficult. In such cases, self-reflection or human review may be more appropriate.

## Deterministic vs LLM Verification

The example uses an LLM as the verifier for simplicity, but in production you might use deterministic verification instead. For passwords, a Python function could check each constraint:

```python
def verify_password(password: str) -> dict[str, bool]:
    return {
        "length_12": len(password) == 12,
        "uppercase_2": sum(1 for c in password if c.isupper()) >= 2,
        "lowercase_2": sum(1 for c in password if c.islower()) >= 2,
        "digits_2": sum(1 for c in password if c.isdigit()) >= 2,
        "special_2": sum(1 for c in password if c in "!@#$%^&*") >= 2,
        "no_consecutive": all(password[i] != password[i+1] for i in range(len(password)-1)),
    }
```

Deterministic verification is faster, cheaper, and perfectly reliable. LLM verification is useful when the criteria are harder to express programmatically, such as "the explanation should be clear to a beginner" or "the code should follow idiomatic patterns."

## Iteration Limits

The loop includes a maximum iteration count:

```python
MAX_ITERATIONS = 5

for iteration in range(max_iterations):
    ...
```

Without a limit, the loop could run indefinitely if the generator keeps producing invalid outputs. The limit provides a safety bound. In practice, if verification fails repeatedly, there may be an issue with the constraints being too strict, the generator prompt being unclear, or a fundamental limitation in what the model can produce.

## Key Differences from Other Patterns

Verification/critique differs from self-reflection in that self-reflection is open-ended introspection while verification checks against explicit criteria. They can be combined: generate, verify against hard constraints, then self-reflect on style or quality.

Verification differs from simple retry. Retry without feedback just runs the same generation again hoping for a different result. Verification provides specific feedback about what failed, enabling targeted improvement.

Verification is related to but distinct from test-driven development. In TDD, tests define correctness and code is written to pass them. In verification/critique, the verifier plays a similar role to tests, but the "code" being verified is LLM output.

## Production Considerations

When implementing verification loops in production, consider cost management since each iteration multiplies API costs. Set reasonable iteration limits and monitor how often the loop runs multiple times. If most requests need many iterations, the generator prompt may need improvement.

Consider latency. Sequential generate-verify-regenerate cycles add up. For user-facing applications, you may need to balance thoroughness against response time.

Invest in good verification prompts. The quality of feedback determines how effectively the generator can improve. Vague feedback like "some constraints failed" is less useful than "constraint 4 failed because there is only 1 special character."

Log verification results. Understanding which constraints fail most often reveals patterns that can inform better generator prompts or constraint definitions.

## Key Takeaways

Verification/critique introduces explicit checking against defined criteria into the generation process. The pattern separates generation and verification into distinct roles, enabling focused prompts and independent evaluation. A feedback loop passes verification failures back to the generator, enabling targeted improvement rather than blind retry. The pattern works best when correctness is objectively checkable and the cost of incorrect output justifies the verification overhead.

The pattern transforms "hope the model gets it right" into "check that the model got it right and fix it if not." This shift from optimism to verification is fundamental to building reliable agentic systems.
