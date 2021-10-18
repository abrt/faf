# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
### Changed
- The `faf pull-components` action no longer adds new components for EOL releases

### Fixed
- Temporary directories after RPM extraction not being cleaned up (#979)
- Fix support for Fedora Rawhide -- branch name changed from "master" to "rawhide"

## [2.4.0] - 2021-06-24
### Added
- Configuration option `hub.banner` in `/etc/faf/plugins/web.conf` to display urgent information in a simple banner at the top of each page

### Changed
- Use file extensions with package LOBs in order to be compatible with debuginfod
- Skip PROVIDES items from RPMs that are longer than 1024 characters

### Fixed
- Various fixes to RHEL 8 builds / Python 3.6 compatibility
- Fix the retrieval of active Fedora versions from the PDC
- Update scripts for Celery 5.0 changes (in a Celery 4.x-compatible way)
- Skip misformatted PROVIDES items in RPM with a warning message, fixing a crash

### Removed
- No logner store CONFLICTS and REQUIRES items from donwloaded RPMs in the database
- Drop dependency on PycURL in favor of the built-in `urllib` module

## [2.3.0] - 2020-09-29
### Added
- History charts to problem pages
- Ability to dissociate bugs from reports in the web interface
- reposync: --no-cache argument to force re-downloading repository metadata
- reposync: Redownload package LOBs when missing

### Changed
- Rename FAF to ABRT Analytics
- Rework container build and deployment to use podman
- Add dependency on cpio
- Add build dependency on python3-werkzeug and python3-cachelib
- Various web interface improvements

### Fixed
- Accommodate for multiple possible debug directories (parallel installable debuginfo in Fedora)
- cleanup-packages: Don’t remove LOBs on dry runs
- reposync: Don’t re-download RPMs with --no-download-rpm

## [2.2.0] - 2020-03-10
### Added
- Autocompletion for faf 
- Option to support/ignore EOL'd releases
- Bundle nodejs libraries whose packages became orphaned
- RHEL8 to Bugzilla product list

### Changed
- Speed up create-problems
- Improve table layout in web UI
- Fix action scheduler
- Web UI improvements
- CLI enhancements
- Simplify/remove internal string encoding conversion
- Fix DB flush-related bug in releasedel
- Fix erroneous counting of unique reports
- Switch from os.listdir to os.scandir where appropriate
- Build fixes

## [2.1.1] - 2019-10-31
### Changed
- Fix RPM unpacking
- Fix flaky test

## [2.1.0] - 2019-10-29
### Added
- Implement new action releasedel
- Many web UI improvements

### Changed
- Rename FAF to ABRT Analytics
- Refactor and improve SQLAlchemy queries
- Allow packages with names up to 256 chars long
- Minor CLI fixes

### Removed
- Remove Dumpdirs

## [2.0.0] - 2019-02-27
### Added
- Add tilde character to allowed characters for version check of packages
- Add a check for unpacked binary path during retracing

### Changed
- Use sqlalchemy defined functions for NULL comparisons
- Modify route for dumpdirs uploads
- Speed-up a query and more descriptive LOBs deletion

### Removed
- Completely drop support of YUM
- Completely drop support of Python2

## [1.3.4] - 2019-01-17
### Added
- Added fedora-messaging schema
- Automatically build FAF in copr
- Show build status badge in README

### Changed
- Migrated from fedmsg to fedora-messaging
- Fixed route to get_hash endpoint
- Fixed bug with uploading dumpdirs
- Logrotate only '.log' files
- Defer loading pickle of known pulled reports

### Removed
- Removed unused CSS styles

## [1.3.3] - 2018-11-14
### Changed
- Full Python3 support
- Full pylint compatibility
- Unbandle css and js libraries

### Added
- Add HACKING guide
- Add Code of Conduct

### Removed
- Remove raw SQL (return back to sqlalchemy)

## [1.3.2] - 2018-06-20
### Changed
- Rewrite main problems query in raw SQL
- Make problems dashboard orderable
- Python3 and Pylint compatibility changes
- Fix spelling

### Added
- Add support of reports archive
- Intuitive reports time filtering
- Make big numbers human readable
- Add possibility to reassign problem components
- Add favicon
- Make pulling comment and attachments for BZ configurable
- Enable matching reports to save
- Create a dropdown menu for signed users
- Allow signed users to see and to delete their data

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

[Unreleased]: https://github.com/abrt/faf/compare/2.4.0...HEAD
[2.4.0]: https://github.com/abrt/faf/compare/2.3.0...2.4.0
[2.3.0]: https://github.com/abrt/faf/compare/2.2.0...2.3.0
[2.2.0]: https://github.com/abrt/faf/compare/2.1.1...2.2.0
[2.1.1]: https://github.com/abrt/faf/compare/2.1.0...2.1.1
[2.1.0]: https://github.com/abrt/faf/compare/2.0.0...2.1.0
[2.0.0]: https://github.com/abrt/faf/compare/1.3.4...2.0.0
[1.3.4]: https://github.com/abrt/faf/compare/1.3.3...1.3.4
[1.3.3]: https://github.com/abrt/faf/compare/1.3.2...1.3.3
[1.3.2]: https://github.com/abrt/faf/compare/1.3.1...1.3.2
[1.3.1]: https://github.com/abrt/faf/compare/1.3.0...1.3.1
[1.3.0]: https://github.com/abrt/faf/compare/1.2.1...1.3.0
[1.2.1]: https://github.com/abrt/faf/compare/1.2.0...1.2.1
[1.2.0]: https://github.com/abrt/faf/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/abrt/faf/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/abrt/faf/compare/0.12...1.0.0
