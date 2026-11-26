import { test as base, type Locator, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { FlowRecorder } from './flow-recorder';

const CLIPS = process.env.FLOW_CLIPS !== 'off';
const AFTER_SECRET_MS = 500;

type Step = { name: string; picture: string; at: number };
type Outcome = 'passed' | 'failed' | null;

export const slug = (text: string) =>
  text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80);

export class FlowPictures {
  private readonly steps: Step[] = [];
  private secretShowing = false;

  constructor(
    private readonly page: Page,
    private readonly folder: string,
    private readonly title: string,
    private readonly recorder?: FlowRecorder,
  ) {}

  async snap(name: string, options: { mask?: Locator[] } = {}): Promise<void> {
    await this.recorder?.still();
    const picture = `${String(this.steps.length + 1).padStart(2, '0')}-${slug(name)}.png`;
    const at = Date.now() / 1000;
    await this.page.screenshot({ path: join(this.folder, picture), mask: options.mask });
    this.steps.push({ name, picture, at });
    this.save(null);
  }

  async secret(act: () => Promise<void>): Promise<void> {
    this.recorder?.pause('a secret was typed');
    this.secretShowing = true;
    await act();
    await new Promise((resolve) => setTimeout(resolve, AFTER_SECRET_MS));
    this.secretShowing = false;
    this.recorder?.resume();
  }

  async finish(failed: boolean): Promise<void> {
    if (failed && !this.secretShowing) await this.snap('Where it stopped').catch(() => undefined);
    await this.recorder?.stop();
    this.save(failed ? 'failed' : 'passed');
  }

  private save(outcome: Outcome): void {
    const size = this.page.viewportSize();
    const flow = { title: this.title, outcome, screen: size && [size.width, size.height], steps: this.steps };
    writeFileSync(join(this.folder, 'flow.json'), `${JSON.stringify(flow, null, 2)}\n`);
  }
}

export const test = base.extend<{ flow: FlowPictures }>({
  flow: async ({ page, browserName }, use, testInfo) => {
    const folder = join(testInfo.project.outputDir, 'pictures', slug(testInfo.title));
    mkdirSync(folder, { recursive: true });
    const recorder = CLIPS && browserName === 'chromium' ? await FlowRecorder.start(page, folder) : undefined;
    const flow = new FlowPictures(page, folder, testInfo.title, recorder);
    await use(flow);
    await flow.finish(testInfo.status !== testInfo.expectedStatus);
  },
});

export { expect } from '@playwright/test';
