'use client';

import { useMemo, useState } from 'react';
import { useSpacetimeDB, useTable, useReducer } from 'spacetimedb/react';
import { tables, reducers } from '@sastaspace/stdb-bindings';
import { relTime, type CommentStatus } from '@/lib/types';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';
import { USE_STDB_ADMIN, useOwnerToken } from '@/hooks/useStdb';

// Phase 3: default-empty after N6. The legacy code path below (USE_STDB_ADMIN
// false branch) fails loud on missing URL rather than calling a dead host.
const ADMIN_API_URL = process.env.NEXT_PUBLIC_ADMIN_API_URL ?? '';

type CommentsProps = { initialFilter?: string; view?: string };

function CommentsInner({ initialFilter = 'pending', view = 'cards' }: CommentsProps) {
  const { isActive } = useSpacetimeDB();
  const [commentRows] = useTable(tables.comment);
  const [userRows] = useTable(tables.user);
  const [moderationRows] = useTable(tables.moderation_event);
  const ownerToken = useOwnerToken();
  const [filter, setFilter] = useState(initialFilter);
  const [postFilter, setPostFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [optimistic, setOptimistic] = useState<Map<bigint, CommentStatus>>(new Map());
  const [confirmDelete, setConfirmDelete] = useState<bigint | null>(null);
  const [actioning, setActioning] = useState<bigint | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Reducer hooks (no-op when no connection, throw when no auth on the wire).
  const setStatusWithReason = useReducer(reducers.setCommentStatusWithReason);
  const deleteCommentReducer = useReducer(reducers.deleteComment);

  const userMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const u of userRows) {
      m.set(u.identity.toHexString(), u.displayName);
    }
    return m;
  }, [userRows]);

  // Latest verdict per comment — surfaces the moderator-agent's reason on flagged rows.
  const verdictMap = useMemo(() => {
    const toMs = (v: unknown) =>
      v instanceof Date ? v.getTime()
        : typeof v === 'bigint' ? Number(v / 1000n)
        : new Date(String(v)).getTime();
    const m = new Map<bigint, string>();
    const sorted = [...moderationRows].sort((a, b) => toMs(a.createdAt) - toMs(b.createdAt));
    for (const ev of sorted) m.set(ev.commentId, ev.reason);
    return m;
  }, [moderationRows]);

  const comments = useMemo(() => {
    return [...commentRows].map(c => {
      const submitterId = c.submitter.toHexString();
      const status = (optimistic.get(c.id) ?? c.status) as CommentStatus;
      const createdAt = c.createdAt instanceof Date ? c.createdAt.toISOString()
        : typeof c.createdAt === 'bigint' ? new Date(Number(c.createdAt / 1000n)).toISOString()
        : String(c.createdAt);
      return {
        id: c.id,
        status,
        author: c.authorName || userMap.get(submitterId) || 'anonymous',
        post: c.postSlug,
        body: c.body,
        createdAt,
        reason: verdictMap.get(c.id) ?? null,
      };
    }).sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [commentRows, userMap, optimistic, verdictMap]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: comments.length, pending: 0, flagged: 0, approved: 0, rejected: 0 };
    comments.forEach(x => { if (c[x.status] !== undefined) c[x.status]++; });
    return c;
  }, [comments]);

  const posts = useMemo(() => Array.from(new Set(comments.map(c => c.post))), [comments]);

  let filtered = comments;
  if (filter !== 'all') filtered = filtered.filter(c => c.status === filter);
  if (postFilter !== 'all') filtered = filtered.filter(c => c.post === postFilter);
  if (search) filtered = filtered.filter(c => c.body.toLowerCase().includes(search.toLowerCase()));

  const writeDisabled = USE_STDB_ADMIN && !ownerToken;

  const setStatus = async (id: bigint, status: CommentStatus, reason: string) => {
    if (writeDisabled) return;
    setActionError(null);
    setActioning(id);
    setOptimistic(prev => new Map(prev).set(id, status));
    try {
      if (USE_STDB_ADMIN) {
        await setStatusWithReason({ id, status, reason });
      } else {
        if (!ADMIN_API_URL) {
          throw new Error('NEXT_PUBLIC_ADMIN_API_URL not set; cannot use legacy admin path. Set NEXT_PUBLIC_USE_STDB_ADMIN=true.');
        }
        const token = localStorage.getItem('admin_token') ?? '';
        const res = await fetch(`${ADMIN_API_URL}/stdb/comments/${id}/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ status }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
      }
    } catch (e) {
      setOptimistic(prev => { const n = new Map(prev); n.delete(id); return n; });
      const msg = e instanceof Error ? e.message : String(e);
      const hint = msg.toLowerCase().includes('not authorized') || msg.toLowerCase().includes('not owner')
        ? 'Not authorized — refresh your STDB owner token in the sidebar settings.'
        : `Action failed: ${msg}`;
      setActionError(hint);
    } finally {
      setActioning(null);
    }
  };

  const doDelete = async () => {
    if (confirmDelete == null) return;
    const id = confirmDelete;
    setConfirmDelete(null);
    if (writeDisabled) return;
    setActionError(null);
    if (USE_STDB_ADMIN) {
      try {
        await deleteCommentReducer({ id });
      } catch (e) {
        // Row stays in the UI because the STDB subscription will not emit a
        // delete event — surface the failure visibly instead of silently ignoring.
        const msg = e instanceof Error ? e.message : String(e);
        const hint = msg.toLowerCase().includes('not authorized') || msg.toLowerCase().includes('not owner')
          ? 'Delete failed: not authorized — refresh your STDB owner token in the sidebar settings.'
          : `Delete failed: ${msg}`;
        setActionError(hint);
      }
    } else {
      if (!ADMIN_API_URL) {
        setActionError('NEXT_PUBLIC_ADMIN_API_URL not set; cannot use legacy admin path. Set NEXT_PUBLIC_USE_STDB_ADMIN=true.');
        return;
      }
      const token = localStorage.getItem('admin_token') ?? '';
      const res = await fetch(`${ADMIN_API_URL}/stdb/comments/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      }).catch((e: unknown) => {
        setActionError(`Delete request failed: ${String(e)}`);
        return null;
      });
      if (res && !res.ok) {
        setActionError(`Delete failed: HTTP ${res.status}`);
      }
    }
  };

  const tabs: CommentStatus[] = ['pending', 'flagged', 'approved', 'rejected'];

  if (!isActive) {
    return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>Connecting to SpacetimeDB…</div>;
  }

  const confirmComment = confirmDelete != null ? comments.find(c => c.id === confirmDelete) : null;

  return (
    <div>
      <div className="filter-bar">
        <div className="tabs">
          <button className={`tab ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
            All <span className="tab__count">{counts.all}</span>
          </button>
          {tabs.map(t => (
            <button key={t} className={`tab ${filter === t ? 'active' : ''}`} onClick={() => setFilter(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
              <span className="tab__count">{counts[t] ?? 0}</span>
            </button>
          ))}
        </div>
        <select className="select" value={postFilter} onChange={e => setPostFilter(e.target.value)}>
          <option value="all">All posts</option>
          {posts.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <div style={{ position: 'relative', flex: 1, maxWidth: 320 }}>
          <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-fg-subtle)', display: 'flex' }}>
            <Icon name="search" size={14}/>
          </span>
          <input className="input" style={{ paddingLeft: 30, width: '100%' }} placeholder="Filter by content…" value={search} onChange={e => setSearch(e.target.value)}/>
        </div>
      </div>

      {writeDisabled && (
        <div className="banner banner--warn" style={{ marginBottom: 14 }}>
          <Icon name="shield-x" size={16}/>
          <span>Moderation actions disabled — paste your STDB owner token in the sidebar settings.</span>
        </div>
      )}
      {actionError && (
        <div className="banner banner--error" style={{ marginBottom: 14 }} role="alert">
          <Icon name="x" size={16}/>
          <span>{actionError}</span>
          <button className="btn btn--ghost" style={{ marginLeft: 'auto', padding: '2px 8px', fontSize: 12 }} onClick={() => setActionError(null)}>Dismiss</button>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--color-fg-muted)' }}>
          {search ? `No comments matching "${search}"` :
           filter === 'pending' ? 'Queue is clear. Nothing needs review.' :
           filter === 'all' ? 'No comments submitted yet.' :
           `No ${filter} comments.`}
        </div>
      )}

      {view === 'cards' && filtered.map(c => (
        <div key={String(c.id)} className="comment-card">
          <div className="comment-card__top">
            <Chip status={c.status}/>
            <span className="comment-card__author">{c.author}</span>
            <span className="comment-card__sep">·</span>
            <span className="comment-card__post">{c.post}</span>
            <span className="comment-card__time" title={c.createdAt}>{relTime(c.createdAt)}</span>
          </div>
          <div className="comment-card__body">{c.body}</div>
          {c.status === 'flagged' && (
            <div className="comment-card__reason" style={{ marginTop: 6, color: 'var(--color-fg-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
              verdict: {c.reason ?? 'unknown'}
            </div>
          )}
          <div className="comment-card__actions">
            {actioning === c.id && <span className="spinner"/>}
            <button className="btn btn--approve" disabled={c.status === 'approved' || actioning === c.id || writeDisabled} onClick={() => void setStatus(c.id, 'approved', 'manual-approve')}><Icon name="check" size={13}/> Approve</button>
            <button className="btn btn--flag" disabled={c.status === 'flagged' || actioning === c.id || writeDisabled} onClick={() => void setStatus(c.id, 'flagged', 'manual-flag')}><Icon name="flag" size={13}/> Flag</button>
            <button className="btn btn--reject" disabled={c.status === 'rejected' || actioning === c.id || writeDisabled} onClick={() => void setStatus(c.id, 'rejected', 'manual-reject')}><Icon name="x" size={13}/> Reject</button>
            <span style={{ flex: 1 }}/>
            <button className="btn btn--danger" disabled={actioning === c.id || writeDisabled} onClick={() => setConfirmDelete(c.id)}><Icon name="trash" size={13}/> Delete</button>
          </div>
        </div>
      ))}

      {view === 'rows' && filtered.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {filtered.map((c, i) => (
            <div key={String(c.id)} style={{ display: 'flex', gap: 14, padding: '14px 18px', borderBottom: i === filtered.length - 1 ? 'none' : '1px solid var(--color-border)', alignItems: 'center' }}>
              <Chip status={c.status}/>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', marginBottom: 3 }}>
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{c.author}</span>
                  <span className="muted" style={{ fontSize: 12 }}>·</span>
                  <span className="comment-card__post" style={{ fontSize: 11 }}>{c.post}</span>
                  <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-fg-subtle)' }}>{relTime(c.createdAt)}</span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--color-fg-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.body}</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn btn--sm btn--approve" disabled={c.status === 'approved' || writeDisabled} onClick={() => void setStatus(c.id, 'approved', 'manual-approve')}>Approve</button>
                <button className="btn btn--sm btn--flag" disabled={c.status === 'flagged' || writeDisabled} onClick={() => void setStatus(c.id, 'flagged', 'manual-flag')}>Flag</button>
                <button className="btn btn--sm btn--danger" disabled={writeDisabled} onClick={() => setConfirmDelete(c.id)}><Icon name="trash" size={12}/></button>
              </div>
            </div>
          ))}
        </div>
      )}

      {confirmComment && (
        <div className="modal-overlay" onClick={() => setConfirmDelete(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__title">Delete this comment?</div>
            <div className="modal__body">
              From <strong style={{ color: 'var(--color-fg)' }}>{confirmComment.author}</strong>. This cannot be undone.
              <div className="modal__quote">{confirmComment.body.slice(0, 80)}{confirmComment.body.length > 80 ? '…' : ''}</div>
            </div>
            <div className="modal__actions">
              <button className="btn btn--ghost" onClick={() => setConfirmDelete(null)}>Cancel</button>
              <button className="btn btn--danger-solid" onClick={() => void doDelete()}><Icon name="trash" size={13}/> Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Comments(props: CommentsProps) {
  return <CommentsInner {...props}/>;
}
