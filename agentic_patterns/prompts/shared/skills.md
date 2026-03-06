## Skills

You have access to skills -- specialized capabilities you can activate on demand.

To use a skill:
1. Call `activate_skill(skill_name)` to load its instructions
2. The instructions will tell you what scripts, references, and assets are available
3. Call `run_skill_script(skill_name, script_name, args)` to execute scripts
4. Call `read_skill_resource(skill_name, resource_type, file_name)` to read references or assets

You must activate a skill before running its scripts or reading its resources.

Available skills:
{skills_catalog}
