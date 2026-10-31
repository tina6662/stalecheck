from stalecheck.manuscript import find_candidates, find_tags, mask_latex_comments


def test_latex_tags_and_lines():
    text = "Intro.\nAccuracy was \\sv{acc}{84.7\\%} and\nn = \\sv{n}{1,024}.\n"
    tags = find_tags(text, latex=True)
    assert [(t.key, t.literal, t.line) for t in tags] == [("acc", "84.7\\%", 2), ("n", "1,024", 3)]
    assert text[tags[0].start:tags[0].end] == "84.7\\%"


def test_markdown_tags():
    text = "Accuracy was 84.7%<!--sv:acc--> (r = -0.31 <!-- sv:corr -->)."
    tags = find_tags(text, latex=False)
    assert [(t.key, t.literal) for t in tags] == [("acc", "84.7%"), ("corr", "-0.31")]


def test_latex_comments_are_ignored():
    text = "kept \\sv{a}{1.0}\n% old: \\sv{b}{2.0} and 3.5%\nescaped 4.5\\% stays\n"
    assert [t.key for t in find_tags(text, latex=True)] == ["a"]
    assert [c.literal for c in find_candidates(text, latex=True)] == ["4.5\\%"]
    assert len(mask_latex_comments(text)) == len(text)


def test_candidates_skip_tags_and_noise():
    text = ("In 2024, see Section 3 and [12]. Accuracy 0.847 rose by 3.2% "
            "(tagged 84.7%<!--sv:acc-->), version 1.2.3.")
    lits = [c.literal for c in find_candidates(text, latex=False)]
    assert lits == ["0.847", "3.2%"]
