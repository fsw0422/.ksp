import type { CDPSession, Page } from '@playwright/test';
import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const STILL_FOR = 0.3;
const STILL_AT_MOST = 2;
const FIRST_FRAME_WAIT = 0.5;
const SHOWN_AFTER = 0.03; // measured: a screencast frame shows a click about 0.03 s after the page's pointerdown
const SWIPE_FROM = 10;

type PageInput = { kind: 'down' | 'up' | 'key'; at: number; x?: number; y?: number };
export type Size = { width: number; height: number };
type Frame = { at: number; data: string };

const now = () => Date.now() / 1000;
const tenth = (at: number) => Math.floor(at * 10);
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export class FlowRecorder {
  private held?: Frame;
  private count = 0;
  private paused = false;
  private lost = false;
  private gotFrame = false;
  private lastMove = 0;
  private resumedAt = 0;
  private readonly started = now();
  private down?: { at: number; place: number[] };

  private constructor(
    private readonly cdp: CDPSession,
    private readonly folder: string,
  ) {}

  static async start(page: Page, flowFolder: string, screen: Size): Promise<FlowRecorder> {
    const folder = join(flowFolder, 'recording');
    mkdirSync(folder, { recursive: true });
    writeFileSync(join(folder, 'frames.jsonl'), '');
    writeFileSync(join(folder, 'inputs.jsonl'), '');
    const cdp = await page.context().newCDPSession(page);
    const recorder = new FlowRecorder(cdp, folder);
    await page.exposeBinding('__flowTestsInput', (_source, input: PageInput) => recorder.take(input));
    await page.addInitScript(listenForInputs);
    page.on('crash', () => recorder.lose('the page crashed'));
    cdp.on('Page.screencastFrame', (frame) => {
      cdp.send('Page.screencastFrameAck', { sessionId: frame.sessionId }).catch((error: Error) => {
        recorder.lose(`the screencast stopped: ${error.message}`);
      });
      recorder.frame({ at: frame.metadata.timestamp ?? now(), data: frame.data });
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 80, maxWidth: screen.width, maxHeight: screen.height });
    return recorder;
  }

  async still(): Promise<void> {
    const began = now();
    while (now() - began < STILL_AT_MOST) {
      const waitingForFirst = !this.gotFrame && now() - this.started < FIRST_FRAME_WAIT;
      if (!waitingForFirst && now() - this.lastMove >= STILL_FOR) return;
      await sleep(20);
    }
  }

  pause(why: string): void {
    this.flush();
    this.paused = true;
    this.down = undefined;
    this.line('frames', { at: now(), pause: why });
  }

  resume(): void {
    this.paused = false;
    this.resumedAt = now();
  }

  async stop(): Promise<void> {
    await this.cdp.send('Page.stopScreencast').catch(() => undefined);
    this.flush();
    if (this.down) this.line('inputs', { at: this.down.at, kind: 'tap', place: this.down.place });
    this.line('frames', { at: now(), end: true });
    await this.cdp.detach().catch(() => undefined);
  }

  private frame(frame: Frame): void {
    this.gotFrame = true;
    this.lastMove = Math.max(this.lastMove, frame.at);
    if (this.paused || this.lost || frame.at < this.resumedAt) return;
    if (this.held && tenth(this.held.at) !== tenth(frame.at)) this.write(this.held);
    this.held = frame;
  }

  private take(input: PageInput): void {
    const at = input.at + SHOWN_AFTER;
    this.lastMove = Math.max(this.lastMove, at);
    if (this.paused) return;
    if (input.kind === 'key') {
      this.line('inputs', { at, kind: 'key' });
    } else if (input.kind === 'down') {
      this.down = { at, place: [input.x ?? 0, input.y ?? 0] };
    } else if (this.down) {
      const to = [input.x ?? 0, input.y ?? 0];
      const moved = Math.hypot(to[0] - this.down.place[0], to[1] - this.down.place[1]) > SWIPE_FROM;
      const ms = Math.round((at - this.down.at) * 1000);
      this.line('inputs', moved
        ? { at: this.down.at, kind: 'swipe', place: this.down.place, to, ms }
        : { at: this.down.at, kind: 'tap', place: this.down.place });
      this.down = undefined;
    }
  }

  private lose(why: string): void {
    if (this.lost) return;
    this.flush();
    this.lost = true;
    this.line('frames', { at: now(), lost: why });
  }

  private flush(): void {
    if (this.held) this.write(this.held);
    this.held = undefined;
  }

  private write(frame: Frame): void {
    const file = `${String(++this.count).padStart(5, '0')}.jpg`;
    writeFileSync(join(this.folder, file), Buffer.from(frame.data, 'base64'));
    this.line('frames', { at: frame.at, frame: file });
  }

  private line(file: 'frames' | 'inputs', entry: object): void {
    appendFileSync(join(this.folder, `${file}.jsonl`), `${JSON.stringify(entry)}\n`);
  }
}

function listenForInputs(): void {
  if (window !== window.top) return;
  const send = (input: object) => (window as unknown as { __flowTestsInput?: (input: object) => void }).__flowTestsInput?.(input);
  const at = (event: Event) => (performance.timeOrigin + event.timeStamp) / 1000;
  const pointer = (kind: string) => (event: PointerEvent) => {
    if (event.isTrusted) send({ kind, at: at(event), x: event.clientX, y: event.clientY });
  };
  addEventListener('pointerdown', pointer('down'), true);
  addEventListener('pointerup', pointer('up'), true);
  for (const kind of ['keydown', 'input']) {
    addEventListener(kind, (event) => event.isTrusted && send({ kind: 'key', at: at(event) }), true);
  }
}
