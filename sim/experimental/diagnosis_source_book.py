"""Physical-source latency and generation-epoch counts for diagnosis jobs."""
from revision_traffic import STAGES, StreamStats, distribution


def counts():
    return dict(generated=0, accepted=0, fired=0)


def population(row):
    g, a, f = (row[key] for key in ("generated", "accepted", "fired"))
    assert g >= a >= f, "source/epoch population conservation"
    return dict(row, pending_outside=g-a, pending_fifo=a-f, pending=g-f)


class SourceBook:
    """Attribute each request to its physical source and its generation window.

    Epochs carry counts only. Per-source latency covers the whole generated
    population; it does not supply an epoch or role-specific latency estimate.
    """

    def __init__(self, n, window, windows):
        self.n, self.window, self.windows = n, window, windows
        self.sources = [counts() for _ in range(n)]
        self.epochs = {self.epoch(k*window): [counts() for _ in range(n)]
                       for k in range(windows+1)}
        self.latency = [{stage: StreamStats() for stage in STAGES} for _ in range(n)]
        self.at_cut = None

    def epoch(self, generation):
        index = min(generation // self.window, self.windows)
        return f"epoch_W{index}" + ("-tail" if index == self.windows else "")

    def charge(self, generation, source, kind):
        self.sources[source][kind] += 1
        self.epochs[self.epoch(generation)][source][kind] += 1

    def observe(self, k, events, accepts, fired):
        for source, _ in events:
            self.charge(k, source, "generated")
        for generation, source in accepts:
            self.charge(generation, source, "accepted")
        if fired is not None:
            generation, acceptance, source = fired
            assert k > acceptance >= generation, "source request time order"
            ga, af, gf = acceptance-generation, k-acceptance, k-generation
            assert ga+af == gf, "request latency identity"
            self.charge(generation, source, "fired")
            for stage, value in zip(STAGES, (ga, af, gf)):
                self.latency[source][stage].add(value)

    def snapshot(self):
        return dict(sources=[population(r) for r in self.sources],
                    epochs={key: [population(r) for r in rows]
                            for key, rows in self.epochs.items()})

    def snapshot_cut(self):
        self.at_cut = self.snapshot()

    def result(self):
        final = self.snapshot()
        assert self.at_cut is not None, "source ledger missing cut"
        for h, row in enumerate(final["sources"]):
            assert row["pending"] == 0, "source population censored at final"
            assert all(s.count == row["fired"] for s in self.latency[h].values())
            for kind in ("generated", "accepted", "fired"):
                assert sum(rows[h][kind] for rows in final["epochs"].values()) == row[kind]
        return dict(
            schema="cxl-diagnosis-physical-sources-v1",
            attribution="physical source; epoch follows generation cycle through switching and drain",
            epoch_statistics="counts only; no epoch latency histogram or P99",
            at_cut=self.at_cut, final=final,
            final_censored=[row["pending"] for row in final["sources"]],
            latency={f"src{h}": {stage: distribution(value) for stage, value in stages.items()}
                     for h, stages in enumerate(self.latency)},
        )
