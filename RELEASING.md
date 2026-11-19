# Releasing aiohappyeyeballs

This document describes the maintainer workflow for publishing aiohappyeyeballs to PyPI and creating the corresponding GitHub Release.

## Set release version and prepare changelog

1. Create a branch `release/1.2.3`.
2. Ensure every user-visible change has a news fragment in `docs/changelog.d/`. Fragment names use the form `<issue-or-pr>.<type>.md`; the available types are defined in `towncrier.toml`.
3. Choose the new version (1.2.3) and update it in both places:

   - `version` in `pyproject.toml`
   - `__version__` in `src/aiohappyeyeballs/__init__.py`

4. Preview the release notes:

   ```console
   $ uvx towncrier build --draft --version 1.2.3
   ```

   Correct the fragments if the rendered notes need changes. Do not edit the generated section in `CHANGELOG.md` by hand.

5. Finalize the changelog using the same version:

   ```console
   $ uvx towncrier build --yes --version 1.2.3
   ```

   The command adds a new `## 1.2.3` section to `CHANGELOG.md` and removes the consumed fragments.

6. Review and commit the version, changelog, and removed fragments. Create a PR, wait for its required checks to pass, and merge it.

## Publish the release

Create an annotated tag from the merged release commit and push it:

```console
$ git switch main
$ git pull --ff-only
$ git tag -a v1.2.3 -m "Release 1.2.3"
$ git push origin v1.2.3
```

The tag version must match `pyproject.toml`, `src/aiohappyeyeballs/__init__.py` and the finalized heading in `CHANGELOG.md`.

Pushing a `v*` tag runs `.github/workflows/ci-cd.yml`, which, after the lint and test jobs pass:

1. Builds the source distribution and wheel and checks them with `twine`.
2. Extracts the Towncrier-generated version section from `CHANGELOG.md`. Missing notes, or a version that differs between the tag, `__version__` and the built distributions, prevent publishing.
3. Publishes the distributions to PyPI through the `pypi` environment and Trusted Publishing.
4. Signs the distributions with Sigstore after PyPI publishing succeeds.
5. Creates the GitHub Release, using the extracted changelog section as its description and attaching the distributions and their Sigstore bundles.

## Verify the release

After the workflow completes:

- Confirm that the expected version and distributions are present on PyPI.
- Confirm that the GitHub Release contains the same notes as `CHANGELOG.md` and includes the source distribution, the wheel, and their Sigstore bundles.
- Install the new version in a clean environment and verify that `aiohappyeyeballs.__version__` reports the expected value.

## Failed releases

- For a transient workflow failure, rerun the failed job.
- If PyPI publishing succeeded but GitHub Release creation failed, rerun the `deploy` job: distributions already on PyPI are skipped and an existing GitHub Release is updated. Do not create a new tag.
- If any distribution reached PyPI, do not move or reuse the version tag. Correct the problem in a new release because published PyPI files are immutable.
- If publishing did not begin and the release commit itself is wrong, correct the release commit before publishing. Avoid changing a tag that users may already have fetched.
