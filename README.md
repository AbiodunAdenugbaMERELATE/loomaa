# Loomaa

Semantic Model as Code for Microsoft Fabric / Power BI.

Loomaa provides an end-to-end workflow:

- `loomaa init` – scaffold an example project
- `loomaa compile` – generate a Fabric/PBIP `.SemanticModel` (TMDL)
- `loomaa view` – local interactive model viewer (Streamlit)
- `loomaa deploy` – deploy to a Fabric workspace via REST API

The default scaffold created by `loomaa init` targets the Microsoft Fabric **Sample Warehouse** tables:
`Trip`, `Medallion`, `Date`, and `Time`.

## Install

```bash
pip install loomaa
```

## Quickstart

```bash
loomaa init my-model
cd my-model
```

This creates an example model under `models/example/` that you can edit.

Compile the model:

```bash
loomaa compile
```

View the model locally:

```bash
loomaa view
```

Deploy to Fabric (requires `.env` values created by `init`):

```bash
loomaa deploy
```

## Output

After `loomaa compile`, output is written under `compiled/`:

- `compiled/<model>/model.json` – viewer-friendly JSON
- `compiled/<model>/<model>.SemanticModel/` – Fabric/PBIP semantic model artifact

## Notes

- Do not commit `.env` (it contains secrets)
- Generated artifacts like `compiled/`, `test_compiled/`, and `*.egg-info/` should not be committed

## License

Apache-2.0
