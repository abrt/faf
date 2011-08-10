// faf-dwarf-files.c - Get source files associated with the dwarf in
// a elf file.
//
// gcc -Wall -g -O2 -lelf -ldw -o faf-dwarf-files faf-dwarf-files.c
//
// Copyright (C) 2011 Mark Wielaard <mjw@redhat.com>
//
// This file is free software.  You can redistribute it and/or modify
// it under the terms of the GNU General Public License (GPL); either
// version 2, or (at your option) any later version.
//
// A big piece of code is from
// https://fedorahosted.org/elfutils/browser/libdw/dwarf_getsrclines.c
// Copyright (C) 2004-2010 Red Hat, Inc.
// Written by Ulrich Drepper <drepper@redhat.com>, 2004.
#include <argp.h>
#include <error.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <byteswap.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <dwarf.h>
#include <libelf.h>
#include <gelf.h>

static bool other_byte_order = false;

#define read_2ubyte_inc(Addr)						\
  ({ uint16_t t_ = (other_byte_order					\
		    ? bswap_16 (*((const uint16_t *) (Addr)))		\
		    : *((const uint16_t *) (Addr)));			\
    Addr = (__typeof (Addr)) (((uintptr_t) (Addr)) + 2);		\
    t_; })

#define read_4ubyte_inc(Addr)						\
  ({ uint32_t t_ = (other_byte_order					\
		    ? bswap_32 (*((const uint32_t *) (Addr)))		\
		    : *((const uint32_t *) (Addr)));			\
    Addr = (__typeof (Addr)) (((uintptr_t) (Addr)) + 4);		\
    t_; })

#define read_8ubyte_inc(Addr)						\
  ({ uint64_t t_ = (other_byte_order					\
		    ? bswap_64 (*((const uint64_t *) (Addr)))		\
		    : *((const uint64_t *) (Addr)));			\
    Addr = (__typeof (Addr)) (((uintptr_t) (Addr)) + 8);		\
    t_; })

static uint64_t
read_uleb128_inc(const unsigned char **addr)
{
  uint64_t result = 0;
  int shift = 0;
  while (true)
    {
      unsigned char byte = **addr;
      *addr += 1;
      result |= (uintmax_t)(byte & 0x7f) << shift;
      if ((byte & 0x80) == 0)
	return result;
      shift += 7;
    }
}

static void
die(const char *s, ...)
{
    va_list p;
    va_start(p, s);
    char *msg;
    if (-1 != vasprintf (&msg, s, p))
      {
	fprintf (stderr, "%s", msg);
	free (msg);
      }
    va_end(p);
    exit (1);
}

int
main (int argc, char **argv)
{
  if (argc != 2)
    error (-1, 0, "Usage %s <file>", argv[0]);

  // Open the ELF file.
  int fd = open (argv[1], O_RDONLY, 0);
  if (fd == -1)
    die ("cannot open `%s': %s\n", argv[1], strerror (errno));

  // Get Elf object for the file.
  elf_version (EV_CURRENT);
  Elf *elf = elf_begin (fd, ELF_C_READ, NULL);
  if (elf == NULL)
    die ("cannot create ELF descriptor: %s\n", elf_errmsg (-1));

  if (elf_kind (elf) != ELF_K_ELF)
    die ("not a valid ELF file\n");

  // Get Elf header.
  GElf_Ehdr ehdr_mem, *ehdr = gelf_getehdr (elf, &ehdr_mem);
  if (ehdr == NULL)
    die ("cannot get ELF header: %s\n", elf_errmsg (-1));

  if ((BYTE_ORDER == LITTLE_ENDIAN && ehdr->e_ident[EI_DATA] == ELFDATA2MSB)
      || (BYTE_ORDER == BIG_ENDIAN && ehdr->e_ident[EI_DATA] == ELFDATA2LSB))
    other_byte_order = true;

  // Loop through all Elf sections and find .debug_* sections.
  const Elf_Data *debug_info = NULL, *debug_line = NULL, *debug_abbrev = NULL;
  const Elf_Data *debug_str = NULL;
  Elf_Scn *scn = NULL;
  while ((scn = elf_nextscn (elf, scn)) != NULL)
    {
      GElf_Shdr shdr_mem, *shdr;

      /* Get the section header data.  */
      shdr = gelf_getshdr (scn, &shdr_mem);
      if (shdr->sh_type == SHT_NOBITS)
	continue;

      if (shdr->sh_flags & SHF_GROUP != 0)
	/* Ignore the section.  */
	continue;

      const char *scnname = elf_strptr (elf, ehdr->e_shstrndx, shdr->sh_name);
      if (scnname == NULL)
	continue;

      const Elf_Data **data = NULL;
      if (strcmp (scnname, ".debug_line") == 0)
	data = &debug_line;
      else if (strcmp (scnname, ".debug_info") == 0)
	data = &debug_info;
      else if (strcmp (scnname, ".debug_abbrev") == 0)
	data = &debug_abbrev;
      else if (strcmp (scnname, ".debug_str") == 0)
	data = &debug_str;
      if (!data)
	continue;

      Elf_Data *check_data = elf_getdata (scn, NULL);
      if (check_data != NULL && check_data->d_size != 0)
	/* Yep, there is actually data available.  */
	*data = check_data;
    }

  if (!debug_info)
      die ("Failed to find .debug_info section.\n");
  if (!debug_line)
      die ("Failed to find .debug_line section.\n");
  if (!debug_abbrev)
      die ("Failed to find .debug_abbrev section.\n");
  // .debug_str is optional

  // Now loop through .debug_info compilation units.
  printf ("CompilationUnits:\n");
  uint64_t next_offset = 0;
  while (next_offset != -1)
    {
      uint64_t offset = next_offset;
      printf("- Offset: %llu\n", offset);
      const unsigned char *dwarf = debug_info->d_buf + offset;
      uint64_t length = read_4ubyte_inc (dwarf);
      size_t offset_size = 4;
      if (length == DWARF3_LENGTH_64_BIT)
	{
	  offset_size = 8;
	  length = read_8ubyte_inc (dwarf);
	}

      // Compute the offset to the next compile unit.
      next_offset = next_offset + 2 * offset_size - 4 + length;
      if (next_offset >= debug_info->d_size)
	next_offset = -1;

      // Read the version stamp. Always a 16-bit value.
      uint16_t version = read_2ubyte_inc (dwarf);

      uint64_t abbrev_offset;
      if (offset_size == 4)
	abbrev_offset = read_4ubyte_inc (dwarf);
      else
	abbrev_offset = read_8ubyte_inc (dwarf);
      printf("  AbbrevOffset: %llu\n", abbrev_offset);

      // The address size. Always an 8-bit value.
      uint8_t address_size = *dwarf++;
      uint64_t die_index = read_uleb128_inc (&dwarf);

      // Find values of DW_AT_name, DW_AT_comp_dir, DW_AT_stmt_list.
      const unsigned char *abbrev = debug_abbrev->d_buf + abbrev_offset;

      uint64_t abbrev_index = read_uleb128_inc (&abbrev);
      if (abbrev_index != die_index)
	die ("abbrev index and die index do not match\n");
      uint64_t abbrev_tag = read_uleb128_inc (&abbrev);
      uint8_t abbrev_child = *abbrev++;

      const char *name = NULL;
      const char *comp_dir = NULL;
      uint64_t statement_list = -1;
      while (true)
	{
	  uint64_t attr = read_uleb128_inc (&abbrev);
	  if (attr == 0)
	    break;

	  uint64_t form = read_uleb128_inc (&abbrev);
	  if (attr == DW_AT_name)
	    {
	      if (form == DW_FORM_string)
		{
		  size_t len = strlen (dwarf);
		  name = dwarf;
		  dwarf += len + 1;
		}
	      else if (form == DW_FORM_strp)
		{
		  if (!debug_str)
		    die ("Failed to find .debug_str section, but it is referenced!\n");
		  uint64_t str_offset;
		  if (offset_size == 4)
		    str_offset = read_4ubyte_inc (dwarf);
		  else
		    str_offset = read_8ubyte_inc (dwarf);
		  name = debug_str->d_buf + str_offset;
		}
	      else
		  die ("unknown DW_FORM for DW_AT_name: %llu\n", form);
	    }
	  else if (attr == DW_AT_comp_dir)
	    {
	      if (form == DW_FORM_string)
		{
		  size_t len = strlen(dwarf);
		  comp_dir = dwarf;
		  dwarf += len + 1;
		}
	      else if (form == DW_FORM_strp)
		{
		  if (!debug_str)
		    die ("Failed to find .debug_str section, but it is referenced!\n");
		  uint64_t str_offset;
		  if (offset_size == 4)
		    str_offset = read_4ubyte_inc (dwarf);
		  else
		    str_offset = read_8ubyte_inc (dwarf);
		  comp_dir = debug_str->d_buf + str_offset;
		}
	      else
		  die ("unknown DW_FORM for DW_AT_comp_dir: %llu\n", form);
	    }
	  else if (attr == DW_AT_stmt_list)
	    {
	      switch (form)
		{
		case DW_FORM_sec_offset:
		  if (offset_size == 4)
		    statement_list = read_4ubyte_inc (dwarf);
		  else
		    statement_list = read_8ubyte_inc (dwarf);
		  break;
		case DW_FORM_data4:
		  statement_list = read_4ubyte_inc (dwarf);
		  break;
		case DW_FORM_data8:
		  statement_list = read_8ubyte_inc (dwarf);
		  break;
		default:
		  die ("unknown DW_FORM for DW_AT_stmt_list\n");
		};
	    }
	  else if (attr != 0)
	    {
	      // Just move the dwarf pointer.
	      switch (form)
		{
		case DW_FORM_addr:
		  dwarf += address_size;
		  break;
		case DW_FORM_string:
		  dwarf += strlen(dwarf) + 1;
		  break;
		case DW_FORM_strp:
		case DW_FORM_sec_offset:
		  dwarf += offset_size;
		  break;
		case DW_FORM_data1: dwarf += 1; break;
		case DW_FORM_data2: dwarf += 2; break;
		case DW_FORM_data4: dwarf += 4; break;
		case DW_FORM_data8: dwarf += 8; break;
		default:
		  die ("unknown DW_FORM to be skipped in compilation unit at offset %llu: %llu\n",
		       (unsigned long long)offset, (unsigned long long)form);
		}
	    }
	}

      if (name) // Name cannot be mandatory, some units do not contain it.
	printf ("  Name: %s\n", name);
      if (comp_dir)
	printf ("  CompDir: %s\n", comp_dir);
      if (statement_list == -1)
	continue;

      printf ("  LineTableOffset: %llu\n", statement_list);
      const unsigned char *line = debug_line->d_buf + statement_list;

      uint64_t unit_length = read_4ubyte_inc (line);
      int line_address_length = 4;
      if (unit_length == DWARF3_LENGTH_64_BIT)
	{
	  unit_length = read_8ubyte_inc (line);
	  line_address_length = 8;
	}

      /* For most tables in .debug_line sections in Fedora binaries,
	 this is a DWARF version, 2 to 4. However for some tables it
	 is 0, or some random large number.  If it is not between 2
	 and 4, eu-readelf -wline does not display the section.
      */
      uint16_t line_version = read_2ubyte_inc (line);
      printf ("  LineTableVersion: %u\n", (unsigned)line_version);
      if (line_version < 2 || line_version > 4)
	continue;

      /* Next comes the header length. */
      uint64_t header_length;
      if (line_address_length == 4)
	header_length = read_4ubyte_inc (line);
      else
	header_length = read_8ubyte_inc (line);

      const unsigned char *header_start = line;

      /* Next the minimum instruction length. */
      uint8_t minimum_instr_len = *line++;
      /* Next the maximum operations per instruction, in version 4 format. */
      uint8_t max_ops_per_instr = 1;
      if (line_version >= 4)
	  max_ops_per_instr = *line++;
      /* Then the flag determining the default value of the is_stmt
	 register. */
      uint8_t default_is_stmt = *line++;
      /* Now the line base. */
      int8_t line_base = (int8_t)*line++;
      /* And the line range. */
      uint_fast8_t line_range = *line++;
      /* The opcode base. */
      uint_fast8_t opcode_base = *line++;

      /* Remember array with the standard opcode length (-1 to account for
	 the opcode with value zero not being mentioned). */
      const uint8_t *standard_opcode_lengths = line - 1;
      line += opcode_base - 1;

      if (*line != 0)
	printf ("  Directories:\n");
      while (*line != 0)
	{
	  printf("  - %s\n", (char*)line);
	  line += strlen(line) + 1;
	}
      /* Skip the final NUL byte. */
      ++line;

      if (*line != 0)
	printf ("  Files:\n");
      while (*line != 0)
	{
         /* First comes the file name. */
	 printf ("  - Path: %s\n", (char*)line);
         line += strlen (line) + 1;
         /* Then the index. */
         uint64_t diridx = read_uleb128_inc (&line);
	 printf ("    DirectoryIndex: %llu\n", diridx);
         /* Next comes the modification time. */
	 read_uleb128_inc (&line);
         /* Finally the length of the file. */
         read_uleb128_inc (&line);
       }
      /* Skip the final NUL byte. */
      ++line;

      /* Consistency check. */
      if (line != header_start + header_length)
	{
	  die ("Invalid .debug_lines header. Header was supposed to be %llu bytes long, but it is %llu bytes long.\n",
	       (unsigned long long)header_length, (unsigned long long)(line - header_start));
	}
    }

  /* Free resources allocated for ELF. */
  elf_end (elf);
  return 0;
}
