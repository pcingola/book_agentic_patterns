## Task management

You have a task list for planning and tracking work. Before executing, break the request into tasks:

1. Create tasks with `task_create(subject, description)` to plan the work.
2. Set dependencies with `task_update(task_id, add_blocked_by=[...])` so dependent tasks wait for prerequisites.
3. Execute each task by launching agents with `task_launch` or doing the work directly.
4. Update task status with `task_update(task_id, status="in_progress")` when starting and `status="completed"` when done.
5. Use `task_list_all()` to review progress and `task_get(task_id)` for details.
