# Rebuild the Thunderbird package

Use Python 3, Blender 4.2 LTS with its COLLADA exporter, and LuaJIT or Lua for the optional RLS source check. Blender 4.2.9 was used for the initial build. A newer Blender release may require a separate COLLADA exporter.

## Generate the vehicle

Run these commands from the project directory. Replace `blender` with your Blender executable's path.

```sh
python3 tools/build_physics.py
blender --background --threads 6 --python tools/build_model.py
python3 tools/validate_package.py
blender --background --threads 4 --python tools/validate_model.py
python3 tools/check_rls.py
python3 tools/package.py
```

`build_physics.py` writes the JBeam and configuration files. `build_model.py` exports the DAE and materials, saves the editable Blender scene, and renders selector thumbnails. Run these in order because the model build adds mesh bindings to the generated JBeam.

`check_rls.py` downloads published RLS 2.8.0 source files into the ignored `references` directory. It runs the source's metadata-shape and dealer-filter functions in Lua. Those checks do not launch BeamNG or RLS. They do not exercise the virtual filesystem, actual stock generation, repairs, or saves.

`validate_model.py` reimports the shipped DAE into an empty Blender scene. It checks mesh names, geometry scale, and a linear suspension constraint matrix. Blender can return a zero process code after some Python failures. Check its output for a traceback and confirm that `model-validation.json` is current.

## Change the vehicle

Edit `source/spec.json` to change engine curves, dimensions, mass targets, or transmission ratios. The body surfaces are generated in `tools/build_model.py`. Suspension attachment geometry is generated in `tools/build_physics.py`.

Rebuilding replaces generated files in `build`, `renders`, and `source`. Keep hand-edited Blender scenes under a different name. Packaging does not include Blender binaries or downloaded reference files.

## Read the reports

- `validation.json` records file checks, selected parts, nominal mass budgets, and estimated engine output.
- `model-validation.json` records DAE round-trip checks and the constraint rank.
- `rls-validation.json` records RLS source hashes and matching dealer filters.
- `dist/SHA256SUMS.txt` records hashes of the distribution ZIPs.

The reports describe local checks. Use [TESTING.md](TESTING.md) to collect the missing game results.
