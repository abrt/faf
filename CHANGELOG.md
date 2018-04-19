# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

## [1.3.1] - 2018-04-19
### Changed
- Import all storage events
- Pull releases and components from PDC
- Pull acls from Pagure
- Do not show any problems when querying unknown component

### Added
- Limit the number of exception mails
- First version of making code Python3 compatible

## [1.3.0] - 2018-03-05
### Changed
- Accept kerneloops without addresses
- Always check validity of ureport
- Order external urls by incoming time
- Improve and update specfile
- Split docker into FAF and DB

### Added
- Enable setting DB parameters with ENV arguments
- Introduce docker DB image
- Introduce OpenShift templates

## [1.2.1] - 2017-10-25
### Changed
- Update to new bugzilla

### Added
- Introduced Docker image
- Support for problems from unpackaged files

## [1.2.0] - 2017-09-12
### Changed
- Private bugzillas are considered unknown
- Accept more dumpdir names

### Added
- New action for checking repositories
- Create problems with speedup option
- Add more info on dumdir page
- Enable setting sender of email

## [1.1.0] - 2017-04-26
### Changed
- Do not exit reposync action when incorrect URL is used
- Fix incorrect URLs in FedMsg
- Speed up action assign_release_to_builds

### Added
- Make saving unknown reports configurable

## [1.0.0] - 2017-03-28
### Changed
- Fixes associated with UTF-8
- Better display of problems.item
- Show maintainer's components by default when logged in
- Use patternfly theme
- Optimization of create_problems
- Updated README
- Semantic versioning

### Added
- Introduce logrotate
- Support mirrors for repositories
- Show unique
- Use link between releases and builds
- Add FIXED status for problems
- Add more tainted flags
- Show frame addresses and build IDs
- Add filter for probably fixed problems
- Support ruby problems
- Allow maintainers to associate BZ with reports
- Show contact emails to maintainers
- Show crash function in reports.list
- Support caching
- Show tainted labels
- Contribution guidelines
- Support for attaching URLs to reports
- Configurable attachment type filtering (Ureport.AcceptAttachments config variable)

## [0.12] - 2015-09-24
### Changed
- Complete rewrite of core and web parts of faf

[Unreleased]: https://github.com/abrt/faf/compare/1.3.1...HEAD
[1.3.1]: https://github.com/abrt/faf/compare/1.3.0...1.3.1
[1.3.0]: https://github.com/abrt/faf/compare/1.2.1...1.3.0
[1.2.1]: https://github.com/abrt/faf/compare/1.2.0...1.2.1
[1.2.0]: https://github.com/abrt/faf/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/abrt/faf/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/abrt/faf/compare/0.12...1.0.0
