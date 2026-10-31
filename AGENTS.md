# Antigravity Global Guidelines & Ambient Status Lighting Protocol

## Smart Lamp Ambient Status Lighting

This repository provides an ambient status signaling protocol that AI coding assistants (Antigravity, Claude Code, Cursor, Cline, etc.) can follow to reflect their internal state in physical room lighting:

### Protocol Rules:
1. **Only if Lamp is ON**:
   - Only change colors if the Lamp is already turned ON.
   - If the lamp is OFF, do not turn it on.
   - The CLI command `wiz signal <type>` automatically checks whether the lamp is ON and safely skips if OFF, while preserving the user's current brightness setting.

2. **Needs User Input / Confirmation**:
   - When the agent needs the user's help, approval, or before asking a question / waiting for input:
     ```bash
     wiz signal blue
     ```
   - When the user replies or work resumes:
     ```bash
     wiz signal warm
     ```

3. **Issue / Error Occurred**:
   - When a build error, test failure, exception, or problem occurs:
     ```bash
     wiz signal red
     ```
   - Once the issue is fixed or work continues:
     ```bash
     wiz signal warm
     ```

4. **Task Completed / Success**:
   - When a task or user request is successfully completed:
     ```bash
     wiz signal green
     ```
     *(Automatically stays Green for 10 seconds, then smoothly reverts to default Warm White in the background).*

5. **Normal State**:
   - Default state is **Warm White** (`2700K`).
