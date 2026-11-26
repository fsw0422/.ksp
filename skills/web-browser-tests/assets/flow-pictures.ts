import { test as base, type Locator, type Page, type TestInfo } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { FlowRecorder, type Size } from './flow-recorder';

const CLIPS = process.env.FLOW_CLIPS !== 'off';
const AFTER_SECRET_MS = 500;

type Step = { name: string; picture: string; at: number };
type Outcome = 'passed' | 'failed' | null;

export const slug = (text: string) =>
  text.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60).replace(/^-+|-+$/g, '');

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// The second half of a test's ID differs for each test and project, and stays the same from run to run.
const folderName = (testInfo: TestInfo) =>
  `${slug(testInfo.titlePath.slice(1).join(' ')) || 'flow'}-${testInfo.testId.slice(-8)}`;

const screenOf = async (page: Page): Promise<Size> =>
  page.viewportSize() ?? page.evaluate(() => ({ width: innerWidth, height: innerHeight }));

export class FlowPictures {
  private readonly steps: Step[] = [];
  private secretShowing = false;

  constructor(
    private readonly page: Page,
    private readonly folder: string,
    private readonly title: string,
    private readonly screen: Size,
    private readonly recorder?: FlowRecorder,
  ) {}

  async snap(name: string, options: { mask?: Locator[] } = {}): Promise<void> {
    if (this.secretShowing) throw new Error(`No step picture while a secret shows: take "${name}" after flow.secret()`);
    await this.recorder?.still();
    const picture = `${String(this.steps.length + 1).padStart(2, '0')}-${slug(name)}.png`;
    const at = Date.now() / 1000;
    await this.page.screenshot({ path: join(this.folder, picture), mask: options.mask });
    this.steps.push({ name, picture, at });
    this.save(null);
  }

  async secret(field: Locator, act: () => Promise<void>): Promise<void> {
    this.recorder?.pause('a secret was typed');
    this.secretShowing = true;
    await act();
    await field.waitFor({ state: 'hidden' });
    await sleep(AFTER_SECRET_MS);
    this.secretShowing = false;
    this.recorder?.resume();
  }

  async finish(failed: boolean): Promise<void> {
    if (failed && !this.secretShowing) await this.snap('Where it stopped').catch(() => undefined);
    await this.recorder?.stop();
    this.save(failed ? 'failed' : 'passed');
  }

  private save(outcome: Outcome): void {
    const screen = [this.screen.width, this.screen.height];
    const flow = { title: this.title, outcome, screen, steps: this.steps };
    writeFileSync(join(this.folder, 'flow.json'), `${JSON.stringify(flow, null, 2)}\n`);
  }
}

export const test = base.extend<{ flow: FlowPictures }>({
  flow: async ({ page, browserName }, use, testInfo) => {
    const folder = join(testInfo.project.outputDir, 'pictures', folderName(testInfo));
    mkdirSync(folder, { recursive: true });
    const screen = await screenOf(page);
    const recorder = CLIPS && browserName === 'chromium' ? await FlowRecorder.start(page, folder, screen) : undefined;
    const flow = new FlowPictures(page, folder, testInfo.title, screen, recorder);
    await use(flow);
    await flow.finish(testInfo.status !== testInfo.expectedStatus);
  },
});

export { expect } from '@playwright/test';
