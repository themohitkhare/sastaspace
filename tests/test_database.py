# tests/test_database.py

from sastaspace.database import (
    JobStatus,
    count_recent_jobs,
    create_job,
    get_job,
    init_db,
    list_jobs,
    list_sites,
    register_site,
    update_job,
)


async def test_create_and_get_job():
    job = await create_job(job_id="j1", url="https://example.com", client_ip="1.2.3.4")
    assert job["id"] == "j1"
    assert job["status"] == JobStatus.QUEUED.value

    fetched = await get_job("j1")
    assert fetched is not None
    assert fetched["url"] == "https://example.com"


async def test_get_nonexistent_job():
    result = await get_job("nonexistent")
    assert result is None


async def test_update_job_status():
    await create_job(job_id="j2", url="https://example.com", client_ip="1.2.3.4")
    await update_job("j2", status=JobStatus.CRAWLING.value, progress=10, message="Crawling...")

    job = await get_job("j2")
    assert job["status"] == JobStatus.CRAWLING.value
    assert job["progress"] == 10


async def test_update_job_done_sets_completed_at():
    await create_job(job_id="j3", url="https://example.com", client_ip="1.2.3.4")
    await update_job("j3", status=JobStatus.DONE.value, progress=100, subdomain="example-com")

    job = await get_job("j3")
    assert job["completed_at"] is not None
    assert job["subdomain"] == "example-com"


async def test_update_job_failed_sets_completed_at():
    await create_job(job_id="j4", url="https://example.com", client_ip="1.2.3.4")
    await update_job("j4", status=JobStatus.FAILED.value, error="timeout")

    job = await get_job("j4")
    assert job["completed_at"] is not None
    assert job["error"] == "timeout"


async def test_list_jobs():
    await create_job(job_id="a1", url="https://a.com", client_ip="1.1.1.1")
    await create_job(job_id="a2", url="https://b.com", client_ip="1.1.1.1")

    jobs = await list_jobs()
    assert len(jobs) == 2


async def test_list_jobs_by_status():
    await create_job(job_id="b1", url="https://a.com", client_ip="1.1.1.1")
    await create_job(job_id="b2", url="https://b.com", client_ip="1.1.1.1")
    await update_job("b2", status=JobStatus.DONE.value)

    done_jobs = await list_jobs(status=JobStatus.DONE.value)
    assert len(done_jobs) == 1
    assert done_jobs[0]["id"] == "b2"


async def test_register_and_list_sites():
    await create_job(job_id="s1", url="https://example.com", client_ip="1.1.1.1")
    await register_site(
        subdomain="example-com",
        original_url="https://example.com",
        job_id="s1",
        html_path="/sites/example-com/index.html",
    )

    sites = await list_sites()
    assert len(sites) == 1
    assert sites[0]["subdomain"] == "example-com"


async def test_count_recent_jobs():
    await create_job(job_id="c1", url="https://a.com", client_ip="5.5.5.5")
    await create_job(job_id="c2", url="https://b.com", client_ip="5.5.5.5")
    await create_job(job_id="c3", url="https://c.com", client_ip="6.6.6.6")

    count = await count_recent_jobs("5.5.5.5", window_seconds=3600)
    assert count == 2

    count_other = await count_recent_jobs("6.6.6.6", window_seconds=3600)
    assert count_other == 1


async def test_create_job_with_tier():
    job = await create_job(
        job_id="t1", url="https://example.com", client_ip="1.1.1.1", tier="premium"
    )
    assert job["tier"] == "premium"

    fetched = await get_job("t1")
    assert fetched["tier"] == "premium"


async def test_init_db_idempotent():
    """Calling init_db multiple times doesn't error."""
    await init_db()
    await init_db()  # Should not raise
