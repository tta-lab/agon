# Session Journal Prompt Draft

This journal is for task sessions (lenos coder, no --agent). Skip it when the
user is just asking a question, chatting, or has no clear task to complete.

When the user gives a task and the runtime hints "you have received a task,
fill the journal before proceeding", do this:

1. Read the journal file at the path the runtime gave you (`JOURNAL=` env var
   or first system message).
2. Fill the initial sections before planning or editing any files. Do not
   edit, create, or modify files until you have filled the journal through
   the Plan section.
3. Treat the journal as the source of truth for current task state.

Use the quote-block instructions inside the template to fill each section.

During work, update the journal only when meaningful state changes occur:

- task interpretation changes
- important context is discovered
- a decision is made
- an approach fails
- files are changed
- verification is run
- the session is ending or handing off

Keep entries short. Do not log every command. Do not narrate routine work.

Prefer facts, decisions, verification results, and next actions.

Before sending a final response or calling exit, explicitly reread and update
these journal sections. Do not skip this step even if the task feels done:

- Progress
- Verification
- Next

If the task is complete, set `Next: none` and fill the `Reflection` section.
If the task failed or was blocked, record what was tried and what remains.

For long work, periodically reread in this order:

- Environment (am I still working in the right context?)
- Deliverables (am I producing the right artifacts?)
- Potential Delivery Risks (what could still go wrong?)
- Existing Verification (am I checking against the right assertions?)
- Failed Paths (am I repeating something that already failed?)
- Verification (what have I actually proven?)

Use that check to avoid repeating failed paths and to keep work pointed at the
requested output. Do not rely on a near-timeout cleanup step; the outer harness
may terminate the run directly.
