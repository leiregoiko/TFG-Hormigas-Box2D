# From Local Forces to Emergent Problem-Solving: Cooperative Transport and Obstacle Negotiation

## Abstract
Ant cooperative transport—groups carrying large loads through cluttered environments—exhibits problem-solving without centralized control. This TFG builds a physics-based, agent-level model of cooperative transport and obstacle negotiation. We formalize mechanisms such as local force alignment, friction anisotropy along walls, and intermittent exploration into a reproducible simulation framework. We map parameters (noise, group size, heterogeneity, communication bandwidth, obstacle geometry) to order parameters (polarization, angular drift) and performance metrics (success rate, time-to-exit, path optimality). The goal is to identify minimal ingredients for robust problem solving and to quantify speed–accuracy trade-offs, with a Quarto-authored report and open-source Python code.

## How to use
1. **Create environment** (example with conda):
   ```bash
   conda env create -f environment.yml
   conda activate tfg
   ```
   Install **Quarto** separately from https://quarto.org/docs/get-started/ .

2. **Run a quick demo**
   ```bash
   make run
   ```

3. **Build the report**
   ```bash
   make report
   ```

4. **Run tests**
   ```bash
   make test
   ```

## Layout
```
.
├─ README.md
├─ environment.yml
├─ Makefile
├─ src/antcoop/
│  ├─ __init__.py
│  └─ demo.py
├─ data/        # generated at runtime
├─ figures/     # generated at runtime
├─ tests/
│  └─ test_basic.py
└─ report/
   ├─ index.qmd
   └─ refs.bib
```

## License
MIT (see LICENSE).