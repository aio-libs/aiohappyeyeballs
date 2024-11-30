# Changelog

## v2.4.4 (2024-11-30)

### Fix

- Handle oserror on failure to close socket instead of raising indexerror (#114) ([`c542f68`](https://github.com/aio-libs/aiohappyeyeballs/commit/c542f684d329fed04093caa2b31d8f7f6e0e0949))

## v2.4.3 (2024-09-30)

### Fix

- Rewrite staggered_race to be race safe (#101) ([`9db617a`](https://github.com/aio-libs/aiohappyeyeballs/commit/9db617a982ee27994bf13c805f9c4f054f05de47))
- Re-raise runtimeerror when uvloop raises runtimeerror during connect (#105) ([`c8f1fa9`](https://github.com/aio-libs/aiohappyeyeballs/commit/c8f1fa93d698f216f84de7074a6282777fbf0439))

## v2.4.2 (2024-09-27)

### Fix

- Copy staggered from standard lib for python 3.12+ (#95) ([`c5a4023`](https://github.com/aio-libs/aiohappyeyeballs/commit/c5a4023d904b3e72f30b8a9f56913894dda4c9d0))

## v2.4.1 (2024-09-26)

### Fix

- Avoid passing loop to staggered.staggered_race (#94) ([`5f80b79`](https://github.com/aio-libs/aiohappyeyeballs/commit/5f80b7951f32d727039d9db776a17a6eba8877cd))

## v2.4.0 (2024-08-19)

### Feature

- Add support for python 3.13 (#86) ([`4f2152f`](https://github.com/aio-libs/aiohappyeyeballs/commit/4f2152fbb6b1d915c2fd68219339d998c47a71f9))

### Documentation

- Fix a trivial typo in readme.md (#84) ([`f5ae7d4`](https://github.com/aio-libs/aiohappyeyeballs/commit/f5ae7d4bce04ee0645257ac828745a3b989ef149))

## v2.3.7 (2024-08-17)

### Fix

- Correct classifier for license python-2.0.1 (#83) ([`186be05`](https://github.com/aio-libs/aiohappyeyeballs/commit/186be056ea441bb3fa7620864f46c6f8431f3a34))

## v2.3.6 (2024-08-16)

### Fix

- Adjust license to python-2.0.1 (#82) ([`30a2dc5`](https://github.com/aio-libs/aiohappyeyeballs/commit/30a2dc57c49d1000ebdafa8c81ecf4f79e35c9f3))

## v2.3.5 (2024-08-07)

### Fix

- Remove upper bound on python requirement (#74) ([`0de1e53`](https://github.com/aio-libs/aiohappyeyeballs/commit/0de1e534fc5b7526e11bf203ab09b95b13f3070b))
- Preserve errno if all exceptions have the same errno (#77) ([`7bbb2bf`](https://github.com/aio-libs/aiohappyeyeballs/commit/7bbb2bf0feb3994953a52a1d606e682acad49cb8))
- Adjust license classifier to better reflect license terms (#78) ([`56e7ba6`](https://github.com/aio-libs/aiohappyeyeballs/commit/56e7ba612c5029364bb960b07022a2b720f0a967))

### Documentation

- Add link to happy eyeballs explanation (#73) ([`077710c`](https://github.com/aio-libs/aiohappyeyeballs/commit/077710c150b6c762ffe408e0ad418c506a2d6f31))

## v2.3.4 (2024-07-31)

### Fix

- Add missing asyncio to fix truncated package description (#67) ([`2644df1`](https://github.com/aio-libs/aiohappyeyeballs/commit/2644df179e21e4513da857f2aea2aa64a3fb6316))

## v2.3.3 (2024-07-31)

### Fix

- Add missing python version classifiers (#65) ([`489016f`](https://github.com/aio-libs/aiohappyeyeballs/commit/489016feb53d4fd5f9880f27dc40a5198d5b0be2))
- Update classifiers to include license (#60) ([`a746c29`](https://github.com/aio-libs/aiohappyeyeballs/commit/a746c296b324407efef272f422a990587b9d6057))
- Workaround broken `asyncio.staggered` on python &lt; 3.8.2 (#61) ([`b16f107`](https://github.com/aio-libs/aiohappyeyeballs/commit/b16f107d9493817247c27ab83522901f086a13b5))
- Include tests in the source distribution package (#62) ([`53053b6`](https://github.com/aio-libs/aiohappyeyeballs/commit/53053b6a38ef868e0170940ced5e0611ebd1be4c))

## v2.3.2 (2024-01-06)

### Fix

- Update urls for the new home for this library (#43) ([`c6d4358`](https://github.com/aio-libs/aiohappyeyeballs/commit/c6d43586d5ca56472892767d4a47d28348158544))

## v2.3.1 (2023-12-14)

### Fix

- Remove test import from tests (#31) ([`c529b15`](https://github.com/aio-libs/aiohappyeyeballs/commit/c529b15fbead0aa5cde9dd5c460ff5abd15fc355))

## v2.3.0 (2023-12-12)

### Feature

- Avoid _interleave_addrinfos when there is only a single addr_info (#29) ([`305f6f1`](https://github.com/aio-libs/aiohappyeyeballs/commit/305f6f13d028ab3ead7923870601175102c5970c))

## v2.2.0 (2023-12-11)

### Feature

- Make interleave with pop_addr_infos_interleave optional to match cpython (#28) ([`adbc8ad`](https://github.com/aio-libs/aiohappyeyeballs/commit/adbc8adfaa44349ca83966787400413668f0b4b6))

## v2.1.0 (2023-12-11)

### Feature

- Add addr_to_addr_info util for converting addr to addr_infos (#27) ([`2e25a98`](https://github.com/aio-libs/aiohappyeyeballs/commit/2e25a98f2339d84bc7951ad17f0b38c104a97a71))

## v2.0.0 (2023-12-10)

### Breaking

- Require the full address tuple for the remove_addr_infos util (#26) ([`d7e5df1`](https://github.com/aio-libs/aiohappyeyeballs/commit/d7e5df12a01838e81729af4c49938e98b3407e03))

## v1.8.1 (2023-12-10)

### Fix

- Move types into a single file (#24) ([`8d4cfee`](https://github.com/aio-libs/aiohappyeyeballs/commit/8d4cfeeaa7862e028e941c49f8c84dcee0b9b1ac))

## v1.8.0 (2023-12-10)

### Feature

- Add utils (#23) ([`d89311d`](https://github.com/aio-libs/aiohappyeyeballs/commit/d89311d1a433dde75863019a08717a531f68befa))

## v1.7.0 (2023-12-09)

### Fix

- License should be psf-2.0 (#22) ([`ca9c1fc`](https://github.com/aio-libs/aiohappyeyeballs/commit/ca9c1fca4d63c54855fbe582132b5dcb229c7591))

### Feature

- Add some more examples to the docs (#21) ([`6cd0b5d`](https://github.com/aio-libs/aiohappyeyeballs/commit/6cd0b5d10357a9d20fc5ee1c96db18c6994cd8fc))

## v1.6.0 (2023-12-09)

### Feature

- Add coverage for multiple and same exceptions (#20) ([`2781b87`](https://github.com/aio-libs/aiohappyeyeballs/commit/2781b87c56aa1c08345d91dce5c1642f2b3e396d))

## v1.5.0 (2023-12-09)

### Feature

- Add coverage for setblocking failing (#19) ([`f759a08`](https://github.com/aio-libs/aiohappyeyeballs/commit/f759a08180f0237cb68d353090f7ba0efe625074))
- Add cover for passing the loop (#18) ([`2d26911`](https://github.com/aio-libs/aiohappyeyeballs/commit/2d26911e9237691c168a705b2d6be2a68fa8b7ac))

## v1.4.1 (2023-12-09)

### Fix

- Ensure exception error is stringified (#17) ([`747cf1d`](https://github.com/aio-libs/aiohappyeyeballs/commit/747cf1d231dc427b79ff1f8128779413a50be5d8))

## v1.4.0 (2023-12-09)

### Feature

- Add coverage for unexpected exception (#16) ([`bad4874`](https://github.com/aio-libs/aiohappyeyeballs/commit/bad48745d3621fcbbe559d55180dc5f5856dc0fa))

## v1.3.0 (2023-12-09)

### Feature

- Add coverage for bind failure with local addresses (#15) ([`f71ec23`](https://github.com/aio-libs/aiohappyeyeballs/commit/f71ec23228d4dad4bc2c3a6630e6e4361b54df44))

## v1.2.0 (2023-12-09)

### Feature

- Add coverage for passing local addresses (#14) ([`72a92e3`](https://github.com/aio-libs/aiohappyeyeballs/commit/72a92e3a599cde082856354e806a793f2b9eff62))

## v1.1.0 (2023-12-09)

### Feature

- Add example usage (#13) ([`707fddc`](https://github.com/aio-libs/aiohappyeyeballs/commit/707fddcd8e8aff27af2180af6271898003ca1782))

## v1.0.0 (2023-12-09)

### Breaking

- Rename create_connection to start_connection (#12) ([`f8b6038`](https://github.com/aio-libs/aiohappyeyeballs/commit/f8b60383d9b9f013baf421ad4e4e183559b7a705))

## v0.9.0 (2023-12-09)

### Feature

- Add coverage for interleave (#11) ([`62817f1`](https://github.com/aio-libs/aiohappyeyeballs/commit/62817f1473bb5702f8fa9edc6f6b24139990cd01))

## v0.8.0 (2023-12-09)

### Feature

- Add coverage for multi ipv6 (#10) ([`6dc8f89`](https://github.com/aio-libs/aiohappyeyeballs/commit/6dc8f89ff99a38c8ecaf8045c9afbe683d6f2c6e))

## v0.7.0 (2023-12-09)

### Feature

- Add coverage for ipv6 failure (#9) ([`7aee8f6`](https://github.com/aio-libs/aiohappyeyeballs/commit/7aee8f64064cfc8d79f385c4dfee45036aacd6fd))

## v0.6.0 (2023-12-09)

### Feature

- Improve test coverage (#8) ([`afcfe5a`](https://github.com/aio-libs/aiohappyeyeballs/commit/afcfe5a350acc50a098009617511cd9d21b22f47))

## v0.5.0 (2023-12-09)

### Feature

- Improve doc strings (#7) ([`3d5f7fd`](https://github.com/aio-libs/aiohappyeyeballs/commit/3d5f7fde55c4bdd4f5e6cff589ae9b47b279d663))

## v0.4.0 (2023-12-09)

### Feature

- Add more tests (#6) ([`4428c07`](https://github.com/aio-libs/aiohappyeyeballs/commit/4428c0714e3e100605f940eb6adee2e86788b4db))

## v0.3.0 (2023-12-09)

### Feature

- Optimize for single case (#5) ([`c7d72f3`](https://github.com/aio-libs/aiohappyeyeballs/commit/c7d72f3cdd13149319fc9e4848146d23bddc619b))

## v0.2.0 (2023-12-09)

### Feature

- Optimize for single case (#4) ([`d371c46`](https://github.com/aio-libs/aiohappyeyeballs/commit/d371c4687d3b3861a4f0287ac5229853f895807b))

## v0.1.0 (2023-12-09)

### Feature

- Init (#2) ([`c9a9099`](https://github.com/aio-libs/aiohappyeyeballs/commit/c9a90994a40d5f49cb37d3e2708db4b4278649ef))

## v0.0.1 (2023-12-09)

### Fix

- Reserve name on pypi (#1) ([`2207f8d`](https://github.com/aio-libs/aiohappyeyeballs/commit/2207f8d361af4ec0b853b07fb743eb957a0b368a))
