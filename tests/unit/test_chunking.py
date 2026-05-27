from research_agent.utils.chunking import chunk_markdown


def test_empty_text_returns_no_chunks():
    assert chunk_markdown("", source_id="x") == []
    assert chunk_markdown("   \n  \n", source_id="x") == []


def test_no_heading_returns_one_chunk():
    chunks = chunk_markdown("just a single short paragraph.", source_id="src_1")
    assert len(chunks) == 1
    assert chunks[0].source_id == "src_1"
    assert chunks[0].heading_path == ""
    assert "single short paragraph" in chunks[0].text


def test_heading_path_built_from_levels():
    text = "# Top\n\nintro.\n\n## Middle\n\nbody.\n\n### Leaf\n\ndetail."
    chunks = chunk_markdown(text, source_id="s")
    paths = [c.heading_path for c in chunks]
    assert "Top" in paths
    assert "Top > Middle" in paths
    assert "Top > Middle > Leaf" in paths


def test_chunk_boundaries_respect_headings():
    text = (
        "## A\n\npara A1 here.\n\npara A2 here.\n\n"
        "## B\n\npara B1 here.\n\npara B2 here."
    )
    chunks = chunk_markdown(text, source_id="s", target_tokens=200, hard_max_tokens=400)
    a_chunks = [c for c in chunks if c.heading_path == "A"]
    b_chunks = [c for c in chunks if c.heading_path == "B"]
    assert a_chunks
    assert b_chunks
    for c in a_chunks:
        assert "B1" not in c.text and "B2" not in c.text


def test_overlap_carries_tail_into_next_chunk():
    para_words = "alpha beta gamma delta epsilon zeta eta theta iota kappa " * 50
    text = f"## H\n\n{para_words}\n\n{para_words}"
    chunks = chunk_markdown(text, source_id="s", target_tokens=80, overlap_tokens=20, hard_max_tokens=120)
    assert len(chunks) >= 2
    assert chunks[0].text[-40:] in chunks[1].text or chunks[0].text[-20:] in chunks[1].text


def test_unique_chunk_ids():
    text = "## A\n\nbody.\n\n## B\n\nbody."
    chunks = chunk_markdown(text, source_id="s")
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
