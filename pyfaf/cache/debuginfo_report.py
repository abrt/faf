# Copyright (C) 2011 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from helpers import *

class DebuginfoReport:
    def __init__(self):
        # Id of the build which was checked
        self.id = None
        # Package maintainers can fix these.
        self.symlinks_pointing_to_another_path = []
        self.debuginfo_missing_for_binary = []
        self.unused_debuginfo = []
        self.missing_source_file_after_build = []
        self.missing_debuginfo_symlink = []
        self.debug_info_section_not_found_in_debug_file = []
        # Package maintainers cannot fix these.
        self.missing_source_file_in_debugsources = []
        self.invalid_version_of_debug_line_table = []
        self.relative_source_name_without_comp_dir = []
        self.missing_comp_dir_referenced_from_debug_lines = []
        self.relative_directory_used_in_debug_lines = []
        self.invalid_directory_offset_in_debug_lines = []

    def issue_count(self):
        count = 0
        for array in [self.symlinks_pointing_to_another_path,
                      self.debuginfo_missing_for_binary,
                      self.unused_debuginfo,
                      self.missing_source_file_after_build,
                      self.missing_debuginfo_symlink,
                      self.debug_info_section_not_found_in_debug_file,
                      self.missing_source_file_in_debugsources,
                      self.invalid_version_of_debug_line_table,
                      self.relative_source_name_without_comp_dir,
                      self.missing_comp_dir_referenced_from_debug_lines,
                      self.relative_directory_used_in_debug_lines,
                      self.invalid_directory_offset_in_debug_lines]:
            count += len(array)
        return count

class SymlinkPointingToAnotherPath:
    def __init__(self):
        # Full path of the affected binary.
        self.path = None
        # Name, version, release of the package where the affected binary is located.
        self.package = None
        # Path to the symlink itself.
        self.debuginfo_symlink_path = None
        # Full path of the binary the symlink is pointing to.
        self.symlink_path = None
        # Name, version, release of the package where the symlink binary is located.
        # Might be empty as the binary might be unpackaged or nonexistant.
        self.symlink_path_package = None

class DebuginfoMissingForBinary:
    def __init__(self):
        # Full path of the binary.
        self.path = None
        # Name, version, release of the package where the binary is located.
        self.package = None
        # Whether the binary is stripped or not
        self.stripped = None
        # Binary file mode.
        self.mode = None

class UnusedDebuginfo:
    def __init__(self):
        # Path to the file containing the symbols.
        self.debuginfo_path = None
        # Path to the missing binary.
        self.binary_path = None
        # Size of the debuginfo file with symbols in bytes.
        self.size = None

class MissingSourceFileDebug:
    def __init__(self):
        # Absolute paths from the debuginfo package.
        self.debug_path = None
        # Source file path or name.
        self.source_file_paths = []

class MissingSourceFile:
    def __init__(self):
        self.package = None
        # Array of MissingSourceFileDebug.
        self.debug_files = []

class MissingDebuginfoSymlink:
    def __init__(self):
        # Path to the missing debuginfo symlink. This is
        # self.binary_symlink + ".debug".
        self.debuginfo_symlink = None
        # Path to the existing build id file, pointing to the binary.
        self.binary_symlink = None
        # Debuginfo package this occured in.
        self.package = None

class DebugInfoSectionNotFoundInDebugFile:
    def __init__(self):
        # Path to the debug file not containing the symbols.
        self.path = None
        # Package containing the path.
        self.package = None

class InvalidVersionOfDebugLineTable:
    def __init__(self):
        # The problematic version number, unknown to DWARF standard.
        self.line_table_version = None
        # Offset of the .debug_line table containing the problematic version number.
        self.line_table_offset = None
        # Offset of the compilation unit referencing the .debug_line table.
        self.compilation_unit_offset = None
        # ELF file with DWARF data containing the .debug_line table.
        self.debuginfo_path = None
        # Debuginfo package containing the path.
        self.package = None

class RelativeSourceNameWithoutCompDir:
    ".debug_info section"
    def __init__(self):
        # Path to the file containing the symbols.
        self.debuginfo_path = None
        # Package containing the path.
        self.package = None
        # Offset of the compilation unit in the .debug_section part of
        # the debuginfo file.
        self.compilation_unit_offset = None
        # Name of the source file.
        self.source_file_name = None

class MissingCompDirReferencedFromDebugLines:
    def __init__(self):
        # Path to the file containing the symbols.
        self.debuginfo_path = None
        # Offset of the compilation unit in the .debug_section part of
        # the debuginfo file, which does not contain the comp_dir entry.
        self.compilation_unit_offset = None
        # Offset of the toplevel table in the .debug_lines part of the
        # debuginfo file, which contains the file referencing the
        # comp_dir entry.
        self.table_offset = None
        # Name of the source file which is in the unknown directory.
        self.source_file_name = None

class RelativeDirectoryUsedInDebugLines:
    def __init__(self):
        # Path to the file containing the symbols.
        self.debuginfo_path = None
        # Offset of the toplevel table in the .debug_lines part of the
        # debuginfo file, which contains the file referencing the
        # relative directory.
        self.table_offset = None
        # Offset of the directory in the directory table.
        self.directory_offset = None
        # Name of the referenced relative directory. All referenced
        # directories must be absolute.
        self.directory_name = None
        # Name of the source file which is in the relative directory.
        self.source_file_name = None
        # If directory_offset is 0, it points to the comp_dir entry in
        # the compilation unit. In this case this is the offset of the
        # compilation unit in the .debug_section part of the debuginfo
        # file, which contains the relative comp_dir entry.
        self.compilation_unit_offset = None

class InvalidDirectoryOffsetInDebugLines:
    def __init__(self):
        # Path to the file containing the symbols.
        self.debuginfo_path = None
        # Offset of the toplevel table in the .debug_lines part of the
        # debuginfo file, which contains the file referencing the
        # relative directory.
        self.table_offset = None
        # The invalid offset of the directory in the directory table.
        self.directory_offset = None
        # Name of the source file which is in the relative directory.
        self.source_file_name = None

missing_source_file_parser = [string("package"),
                              array_dict("debug_files",
                                         MissingSourceFileDebug,
                                         [string("debug_path"),
                                          array_string("source_file_paths")])]

parser = toplevel("debuginfo_report",
                  DebuginfoReport,
                  [int_positive("id"),
                   array_dict("symlinks_pointing_to_another_path",
                              SymlinkPointingToAnotherPath,
                              [string("path"),
                               string("package"),
                               string("debuginfo_symlink_path"),
                               string("symlink_path"),
                               string("symlink_path_package", null=True)]),
                   array_dict("debuginfo_missing_for_binary",
                              DebuginfoMissingForBinary,
                              [string("path"),
                               string("package"),
                               boolean("stripped"),
                               int_positive("mode")]),
                   array_dict("unused_debuginfo",
                              UnusedDebuginfo,
                              [string("debuginfo_path"),
                               string("binary_path"),
                               int_unsigned("size")]),
                   array_dict("missing_source_file_after_build",
                              MissingSourceFile,
                              missing_source_file_parser),
                   array_dict("missing_debuginfo_symlink",
                              MissingDebuginfoSymlink,
                              [string("debuginfo_symlink"),
                               string("binary_symlink"),
                               string("package")]),
                   array_dict("debug_info_section_not_found_in_debug_file",
                              DebugInfoSectionNotFoundInDebugFile,
                              [string("path"),
                               string("package")]),
                   array_dict("missing_source_file_in_debugsources",
                              MissingSourceFile,
                              missing_source_file_parser),
                   array_dict("invalid_version_of_debug_line_table",
                              InvalidVersionOfDebugLineTable,
                              [int_unsigned("line_table_version"),
                               int_unsigned("line_table_offset"),
                               int_unsigned("compilation_unit_offset"),
                               string("debuginfo_path"),
                               string("package")]),
                   array_dict("relative_source_name_without_comp_dir",
                              RelativeSourceNameWithoutCompDir,
                              [string("debuginfo_path"),
                               string("package"),
                               int_unsigned("compilation_unit_offset"),
                               string("source_file_name")]),
                   array_dict("missing_comp_dir_referenced_from_debug_lines",
                              MissingCompDirReferencedFromDebugLines,
                              [string("debuginfo_path"),
                               int_unsigned("compilation_unit_offset"),
                               int_unsigned("table_offset"),
                               string("source_file_name")]),
                   array_dict("relative_directory_used_in_debug_lines",
                              RelativeDirectoryUsedInDebugLines,
                              [string("debuginfo_path"),
                               int_unsigned("table_offset"),
                               int_unsigned("directory_offset"),
                               string("directory_name"),
                               string("source_file_name"),
                               int_unsigned("compilation_unit_offset", null=lambda parent:parent.directory_offset != 0)]),
                   array_dict("invalid_directory_offset_in_debug_lines",
                              InvalidDirectoryOffsetInDebugLines,
                              [string("debuginfo_path"),
                               int_unsigned("table_offset"),
                               int_unsigned("directory_offset"),
                               string("source_file_name")])])
