// Vitest spec for the auth-mailer agent. Mocks Resend + the env, then drives
// the agent with a hand-rolled stub of the StdbConn shape it consumes.

import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("resend", () => {
  const send = vi
    .fn()
    .mockResolvedValue({ data: { id: "msg-fake" }, error: null });
  return {
    Resend: vi.fn().mockImplementation(() => ({
      emails: { send },
    })),
  };
});

vi.mock("../shared/env.js", () => ({
  env: {
    RESEND_API_KEY: "re_fake",
    RESEND_FROM: "test@sastaspace.com",
  },
}));

type FakeRow = {
  id: bigint;
  toEmail: string;
  subject: string;
  bodyHtml: string;
  bodyText: string;
  status: string;
};

const makeRow = (overrides: Partial<FakeRow> = {}): FakeRow => ({
  id: 1n,
  toEmail: "x@y.com",
  subject: "s",
  bodyHtml: "<p>h</p>",
  bodyText: "h",
  status: "queued",
  ...overrides,
});

type StartArg = Parameters<typeof import("./auth-mailer.js").start>[0];

const makeFakeDb = (
  markEmailSent: ReturnType<typeof vi.fn>,
  markEmailFailed: ReturnType<typeof vi.fn>,
  rows: FakeRow[],
) => {
  let onInsertCb: ((ctx: unknown, row: FakeRow) => void) | undefined;
  return {
    db: {
      // satisfy the typed shape we cast to inside auth-mailer.ts
    } as Record<string, unknown> & {
      pendingEmail: {
        iter: () => Iterable<FakeRow>;
        onInsert: (cb: (ctx: unknown, row: FakeRow) => void) => void;
      };
    },
    setOnInsert(cb: (ctx: unknown, row: FakeRow) => void) {
      onInsertCb = cb;
    },
    triggerInsert(row: FakeRow) {
      if (onInsertCb) onInsertCb({}, row);
    },
    fakeConn: {
      subscriptionBuilder: () => ({ subscribe: vi.fn() }),
      reducers: { markEmailSent, markEmailFailed },
      db: {
        pendingEmail: {
          onInsert(cb: (ctx: unknown, row: FakeRow) => void) {
            onInsertCb = cb;
          },
          iter(): Iterable<FakeRow> {
            return rows[Symbol.iterator]();
          },
        },
      },
      disconnect: vi.fn(),
    },
    rows,
  };
};

const wrap = (markEmailSent: ReturnType<typeof vi.fn>, markEmailFailed: ReturnType<typeof vi.fn>, rows: FakeRow[]) => {
  const built = makeFakeDb(markEmailSent, markEmailFailed, rows);
  const arg: StartArg = {
    connection: built.fakeConn as unknown as StartArg["connection"],
    callReducer: vi.fn(),
    subscribe: vi.fn(),
    close: vi.fn().mockResolvedValue(undefined),
  };
  return { arg, built };
};

const flush = () => new Promise((r) => setTimeout(r, 30));

describe("auth-mailer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  it("happy path: drains the seeded queued row + marks sent", async () => {
    const markEmailSent = vi.fn();
    const markEmailFailed = vi.fn();
    const { arg } = wrap(markEmailSent, markEmailFailed, [makeRow()]);

    const { start } = await import("./auth-mailer.js");
    const stop = await start(arg);
    await flush();
    expect(markEmailSent).toHaveBeenCalledTimes(1);
    expect(markEmailSent).toHaveBeenCalledWith({ id: 1n, providerMsgId: "msg-fake" });
    expect(markEmailFailed).not.toHaveBeenCalled();
    await stop();
  });

  it("subscription path: insert callback drives a send", async () => {
    const markEmailSent = vi.fn();
    const markEmailFailed = vi.fn();
    const { arg, built } = wrap(markEmailSent, markEmailFailed, []);

    const { start } = await import("./auth-mailer.js");
    const stop = await start(arg);
    built.triggerInsert(makeRow({ id: 42n, toEmail: "later@y.com" }));
    await flush();
    expect(markEmailSent).toHaveBeenCalledWith({ id: 42n, providerMsgId: "msg-fake" });
    await stop();
  });

  it("ignores non-queued rows on insert", async () => {
    const markEmailSent = vi.fn();
    const markEmailFailed = vi.fn();
    const { arg, built } = wrap(markEmailSent, markEmailFailed, []);

    const { start } = await import("./auth-mailer.js");
    const stop = await start(arg);
    built.triggerInsert(makeRow({ id: 99n, status: "sent" }));
    await flush();
    expect(markEmailSent).not.toHaveBeenCalled();
    expect(markEmailFailed).not.toHaveBeenCalled();
    await stop();
  });

  it("failure: marks failed when resend throws", async () => {
    const markEmailSent = vi.fn();
    const markEmailFailed = vi.fn();

    const { Resend } = await import("resend");
    (Resend as unknown as ReturnType<typeof vi.fn>).mockImplementationOnce(() => ({
      emails: { send: vi.fn().mockRejectedValue(new Error("boom")) },
    }));

    const { arg } = wrap(markEmailSent, markEmailFailed, [makeRow({ id: 7n })]);

    const { start } = await import("./auth-mailer.js");
    const stop = await start(arg);
    await flush();
    expect(markEmailSent).not.toHaveBeenCalled();
    expect(markEmailFailed).toHaveBeenCalledTimes(1);
    expect(markEmailFailed.mock.calls[0]?.[0]).toMatchObject({ id: 7n });
    expect(String((markEmailFailed.mock.calls[0]?.[0] as { error: string }).error)).toContain("boom");
    await stop();
  });

  it("failure: marks failed when resend returns an error envelope", async () => {
    const markEmailSent = vi.fn();
    const markEmailFailed = vi.fn();

    const { Resend } = await import("resend");
    (Resend as unknown as ReturnType<typeof vi.fn>).mockImplementationOnce(() => ({
      emails: {
        send: vi
          .fn()
          .mockResolvedValue({ data: null, error: { message: "rate_limited" } }),
      },
    }));

    const { arg } = wrap(markEmailSent, markEmailFailed, [makeRow({ id: 11n })]);

    const { start } = await import("./auth-mailer.js");
    const stop = await start(arg);
    await flush();
    expect(markEmailSent).not.toHaveBeenCalled();
    expect(markEmailFailed).toHaveBeenCalledTimes(1);
    expect(markEmailFailed.mock.calls[0]?.[0]).toMatchObject({ id: 11n });
    expect(String((markEmailFailed.mock.calls[0]?.[0] as { error: string }).error)).toContain("rate_limited");
    await stop();
  });
});
