---
name: mermaid-image
description: Draw and check Mermaid diagrams. Turns each diagram in a chat reply into a PNG image, offline, and sends it, so it shows on both the desktop and the phone and can be zoomed. Also checks the syntax of diagrams written into files such as specs, which keep their Mermaid text. Use for every Mermaid diagram, such as a flowchart, a sequence diagram, a state diagram, or a review's progress map.
---

# Mermaid Image

Draw Mermaid diagrams that read well everywhere. In a chat reply, turn each diagram into a PNG image and send it. In a file such as a spec, keep the Mermaid text, because GitHub draws it, and check it with the same script.

**Why:** a Mermaid code block shows as plain code on the phone. On the desktop it shrinks to fit the chat, with no way to zoom. A sent image shows on both, and both can zoom it. Sending uploads a copy into the conversation, so the image keeps showing after the local file is gone.

## Make and send an image

1. Write the diagram to a `.mmd` file in a temporary folder: the session's scratchpad in Claude Code, or `$TMPDIR`. Never put it in a repository.
2. Render it with this skill's script:

   ```bash
   python3 -I <this skill's folder>/scripts/render.py restore.mmd restore.png
   ```

3. Send the PNG where the diagram belongs in the reply: write the text that comes before it, send the image, then continue. In Claude Code, use SendUserFile with `status: normal` and no `display`.

For example, `restore.mmd` holds:

```mermaid
flowchart TD
    Open[User reopens a Class] --> Load{Saved audio loads?}
    Load -->|Yes| Play[Class opens with its audio]
    Load -->|No| Retry[Class opens without audio and offers a retry]
```

The script prints the image's path and size, such as `/…/restore.png: 392x534 CSS pixels, saved at 2x`. A diagram takes about a second.

## Draw for a phone screen

- Draw flows top-down, with `flowchart TD`. Use left-to-right only for 4 boxes or fewer, because a wide image turns into a thin strip on a phone.
- Keep labels short. Mermaid wraps a long label onto more lines.
- Show one idea per diagram. Split a big flow into two diagrams instead of drawing one huge one.

## Check the syntax

Every render checks the syntax: the script stops on an error and points at the line. Check a diagram that goes in a file the same way, and don't send its image.

Common traps:

- **A semicolon in a sequence diagram:** a raw `;` in message or note text ends the statement, so `A->>B: load; then play` fails. Reword it, or write `#59;`, which shows as a semicolon.
- **`CLASS` in an ER diagram:** it's a Mermaid keyword. Give that entity another ID, with its name as a label in its own block: `CLS["Class"] { ... }`.

## If it fails

| The script says | What to do |
| --- | --- |
| `Mermaid found a syntax error` | Fix the line it points to, as [Check the syntax](#check-the-syntax) describes, and render again |
| `Chrome for Testing is not installed` | Send a Mermaid code block this time, and give the user the install command it printed |
| `The image came out blank` | Send a Mermaid code block, and tell the user the script needs a fix |
| Anything else | Send a Mermaid code block, and say the image failed |

Where images can't be sent at all, such as in Codex or a terminal, use a Mermaid code block where Mermaid renders, and ASCII where it doesn't.

## How it works

- `assets/mermaid.min.js` is Mermaid 12.2.0 from cdn.jsdelivr.net. Its MIT license is in `assets/LICENSE-mermaid`. Nothing is downloaded while rendering.
- The script opens Mermaid in a windowless, throwaway copy of the browser MCP's Chrome for Testing, which `playwright-chromium-browser/browser.sh path` finds. The copy has an empty profile and no network access. It never touches the shared browser window, its tabs, or its sign-ins, and the diagram never leaves the machine.
- It saves a screenshot at twice the normal pixel density, so text stays sharp when zoomed. Set `MERMAID_IMAGE_BROWSER` to use another Chromium.
- To update Mermaid, download a newer pinned build over `assets/mermaid.min.js`, render a flowchart, a sequence diagram, and a broken diagram, and check the results.
