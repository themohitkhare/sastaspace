// Connection wrapper. Phase 1 workstreams flesh this out with the real
// @clockworklabs/spacetimedb-sdk wiring once the bindings are regenerated
// after their reducers land. For now it's a typed stub so index.ts compiles.

export interface StdbConn {
  callReducer(name: string, ...args: unknown[]): Promise<void>;
  subscribe(query: string, handler: (row: unknown) => void): Promise<void>;
  close(): Promise<void>;
}

export async function connect(_url: string, _module: string, _token: string): Promise<StdbConn> {
  // Phase 1 W1 fills this in. Stubbed to throw so any agent that tries to
  // run before its workstream lands fails loud.
  throw new Error("stdb.connect not implemented yet — Phase 1 W1 deliverable");
}
