"""Real-coded genetic algorithm written from scratch (no EA library).

Operators
  * initialisation : uniform random within bounds (+ optional seed individuals)
  * selection      : k-tournament
  * crossover      : simulated binary crossover (SBX), Deb & Agrawal 1995
  * mutation       : Gaussian (Box-Muller from rng.py), step size shrinks
                     linearly over the run
  * replacement    : generational with elitism
The GA minimises the fitness function.
"""
from rng import RNG


class RealCodedGA:
    def __init__(self, bounds, pop_size=30, generations=40, crossover_rate=0.9,
                 eta_c=15.0, mutation_rate=None, sigma_start=0.15, sigma_end=0.03,
                 tournament_size=3, elites=2, seed=0, seed_individuals=None):
        self.bounds = bounds
        self.n = len(bounds)
        self.pop_size = pop_size
        self.generations = generations
        self.pc = crossover_rate
        self.eta_c = eta_c
        self.pm = mutation_rate if mutation_rate is not None else 1.0 / self.n
        self.sigma_start = sigma_start
        self.sigma_end = sigma_end
        self.k = tournament_size
        self.elites = elites
        self.rng = RNG(seed)
        self.seed_individuals = seed_individuals or []

    # ---------------------------------------------------------- helpers
    def clamp(self, x):
        out = []
        for v, (lo, hi) in zip(x, self.bounds):
            if v < lo:
                v = lo
            elif v > hi:
                v = hi
            out.append(v)
        return out

    def random_individual(self):
        return [self.rng.uniform_range(lo, hi) for lo, hi in self.bounds]

    def tournament(self, pop, fit):
        best = self.rng.randint(0, len(pop) - 1)
        for _ in range(self.k - 1):
            c = self.rng.randint(0, len(pop) - 1)
            if fit[c] < fit[best]:
                best = c
        return pop[best]

    def sbx(self, p1, p2):
        c1, c2 = list(p1), list(p2)
        if self.rng.uniform() > self.pc:
            return c1, c2
        for i in range(self.n):
            if self.rng.uniform() > 0.5:
                continue  # gene inherited unchanged
            u = self.rng.uniform()
            if u <= 0.5:
                beta = (2.0 * u) ** (1.0 / (self.eta_c + 1.0))
            else:
                beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (self.eta_c + 1.0))
            x1, x2 = p1[i], p2[i]
            c1[i] = 0.5 * ((1.0 + beta) * x1 + (1.0 - beta) * x2)
            c2[i] = 0.5 * ((1.0 - beta) * x1 + (1.0 + beta) * x2)
        return self.clamp(c1), self.clamp(c2)

    def mutate(self, x, sigma_frac):
        y = list(x)
        for i, (lo, hi) in enumerate(self.bounds):
            if self.rng.uniform() < self.pm:
                y[i] += sigma_frac * (hi - lo) * self.rng.gauss()
        return self.clamp(y)

    # ---------------------------------------------------------- main loop
    def run(self, evaluate_batch, log=None):
        """evaluate_batch(list_of_genomes) -> list_of_fitness (lower is better)."""
        pop = [self.clamp(list(s)) for s in self.seed_individuals][: self.pop_size]
        while len(pop) < self.pop_size:
            pop.append(self.random_individual())
        fit = evaluate_batch(pop)
        evaluations = len(pop)
        history = []

        for gen in range(self.generations + 1):
            order = sorted(range(len(pop)), key=lambda i: fit[i])
            best_i = order[0]
            history.append({
                "generation": gen,
                "best": fit[best_i],
                "mean": sum(fit) / len(fit),
                "worst": fit[order[-1]],
                "best_genome": list(pop[best_i]),
                "evaluations": evaluations,
            })
            if log:
                log(history[-1])
            if gen == self.generations:
                break

            frac = gen / max(1, self.generations - 1)
            sigma = self.sigma_start + (self.sigma_end - self.sigma_start) * frac

            new_pop = [list(pop[i]) for i in order[: self.elites]]
            new_fit = [fit[i] for i in order[: self.elites]]
            children = []
            while len(new_pop) + len(children) < self.pop_size:
                p1 = self.tournament(pop, fit)
                p2 = self.tournament(pop, fit)
                c1, c2 = self.sbx(p1, p2)
                children.append(self.mutate(c1, sigma))
                if len(new_pop) + len(children) < self.pop_size:
                    children.append(self.mutate(c2, sigma))
            child_fit = evaluate_batch(children)
            evaluations += len(children)
            pop = new_pop + children
            fit = new_fit + child_fit

        return history[-1]["best_genome"], history[-1]["best"], history
