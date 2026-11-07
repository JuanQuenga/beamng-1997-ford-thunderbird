# Contribute to the Thunderbird

Fork this repository, make your changes on a branch, and open a pull request. Use issues to report problems or discuss larger changes.

Useful contributions include in-game testing, more accurate body geometry, suspension tuning, crash deformation, working lights and instruments, and RLS purchase and repair testing.

## Change the source files

Edit the generators in `tools` and specifications in `source/spec.json` for changes that must survive a rebuild. Follow [BUILD.md](BUILD.md) to regenerate the game files and run local checks.

If you edit the Blender scene by hand, include the edited `.blend` file and explain which generated files it replaces. The model generator overwrites `source/thunderbird_1997.blend` on its next run.

Include updated game files and validation reports when your change affects the packaged mod. Update the distribution ZIPs and their checksums with `tools/package.py`.

## Describe verification

State the BeamNG version, RLS version, configuration, map, and tests you ran. Distinguish file checks from actual game tests. Follow [TESTING.md](TESTING.md) when reporting driving or career results.

## Include assets you can share

Include only assets you created or have permission to redistribute. Document the source and license of external assets. The project's MIT license covers its original files, while Ford names and third-party assets retain their own rights.
