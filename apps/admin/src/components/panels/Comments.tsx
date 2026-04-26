'use client';

import { useMemo, useState } from 'react';
import { useSpacetimeDB, useTable } from 'spacetimedb/react';
import { tables } from '@sastaspace/stdb-bindings';
import { relTime, type CommentStatus } from '@/lib/data';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';

const ADMIN_API_URL = process.env.NEXT_PUBLIC_ADMIN_API_URL ?? 'https://api.sastaspace.com';

type CommentsProps = { initialFilter?: string; view?: string };

function CommentsInner({ initialFilter = 'pending', view = 'cards' }: CommentsProps) {
  const { isActive } = useSpacetimeDB();
  const [commentRows] = useTable(tables.comment);
  const [userRows] = useTable(tables.user);
  const [filter, setFilter] = useState(initialFilter);
  const [postFilter, setPostFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [optimistic, setOptimistic] = useState<Map<bigint, CommentStatus>>(new Map());
  const [confirmDelete, setConfirmDelete] = useState<bigint | null>(null);
  const [actioning, setActioning] = useState<bigint | null>(null);

  const userMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const u of userRows) {
      m.set(u.identity.toHexString(), u.displayName);
    }
    return m;
  }, [userRows]);

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
      };
    }).sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [commentRows, userMap, optimistic]);

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

  const token = typeof window !== 'undefined' ? localStorage.getItem('admin_token') ?? '' : '';

  const setStatus = async (id: bigint, status: CommentStatus) => {
    setActioning(id);
    setOptimistic(prev => new Map(prev).set(id, status));
    try {
      const res = await fetch(`${ADMIN_API_URL}/stdb/comments/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch {
      // revert optimistic update on failure
      setOptimistic(prev => { const n = new Map(prev); n.delete(id); return n; });
    } finally {
      setActioning(null);
    }
  };

  const doDelete = async () => {
    if (confirmDelete == null) return;
    const id = confirmDelete;
    setConfirmDelete(null);
    try {
      await fetch(`${ADMIN_API_URL}/stdb/comments/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch { /* STDB subscription will reflect the delete */ }
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
          <div className="comment-card__actions">
            {actioning === c.id && <span className="spinner"/>}
            <button className="btn btn--approve" disabled={c.status === 'approved' || actioning === c.id} onClick={() => void setStatus(c.id, 'approved')}><Icon name="check" size={13}/> Approve</button>
            <button className="btn btn--flag" disabled={c.status === 'flagged' || actioning === c.id} onClick={() => void setStatus(c.id, 'flagged')}><Icon name="flag" size={13}/> Flag</button>
            <button className="btn btn--reject" disabled={c.status === 'rejected' || actioning === c.id} onClick={() => void setStatus(c.id, 'rejected')}><Icon name="x" size={13}/> Reject</button>
            <span style={{ flex: 1 }}/>
            <button className="btn btn--danger" disabled={actioning === c.id} onClick={() => setConfirmDelete(c.id)}><Icon name="trash" size={13}/> Delete</button>
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
                <button className="btn btn--sm btn--approve" disabled={c.status === 'approved'} onClick={() => void setStatus(c.id, 'approved')}>Approve</button>
                <button className="btn btn--sm btn--flag" disabled={c.status === 'flagged'} onClick={() => void setStatus(c.id, 'flagged')}>Flag</button>
                <button className="btn btn--sm btn--danger" onClick={() => setConfirmDelete(c.id)}><Icon name="trash" size={12}/></button>
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
