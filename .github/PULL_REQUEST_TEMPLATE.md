<!-- Thank you for your contribution! -->

## What do these changes do?

<!-- Please give a short brief about these changes. -->

## Are there changes in behavior for the user?

<!-- Outline any notable behaviour for the end users. -->

## Is it a substantial burden for the maintainers to support this?

<!--
Stop right there! Pause. Just for a minute... Can you think of anything
obvious that would complicate the ongoing development of this project?

Try to consider if you'd be able to maintain it throughout the next
5 years. Does it seem viable? Tell us your thoughts! We'd very much
love to hear what the consequences of merging this patch might be...

This will help us assess if your change is something we'd want to
entertain early in the review process. Thank you in advance!
-->

## Related issue number

<!--
Are there any issues opened that will be resolved by merging this change?
Remember to prefix with 'Fixes' if it closes an issue (e.g. 'Fixes #123').
-->

## Checklist

- [ ] I think the code is well written
- [ ] Unit tests for the changes exist
- [ ] Documentation reflects the changes
- [ ] Add a new news fragment into the `docs/changelog.d/` folder
  - name it `<issue_or_pr_num>.<category>.md`, for example `123.bugfix.md`
  - if you don't have an issue number, change it to the pull request
    number after creating the PR
  - the categories are listed in
    [`docs/changelog.d/README.md`](https://github.com/aio-libs/aiohappyeyeballs/blob/main/docs/changelog.d/README.md)
  - use the past tense and explain the effect on end users, for example:
    ```md
    Fixed a crash when `start_connection()` received an empty list
    of addresses -- by {user}`github-username`.
    ```
  - PRs that don't need a fragment (dependency bumps, CI tweaks) can get
    the `bot:chronographer:skip` label instead
