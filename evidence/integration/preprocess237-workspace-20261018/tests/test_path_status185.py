"""Containment and no-follow regression for status-only local paths."""
from pathlib import Path
import os
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app.collection_status import local_file

class StatusLocalPaths185Tests(unittest.TestCase):
    def test_relative_absolute_and_normalized_internal_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(); (root/'nested').mkdir(); target=root/'nested/file.tif'; target.write_bytes(b'x')
            with patch.object(Path,'resolve',side_effect=AssertionError('per-file realpath forbidden')):
                for value in ('nested/file.tif',str(target),'nested/../nested/file.tif'):
                    self.assertEqual(local_file(value,root),target)

    def test_outside_paths_rejected_before_lstat(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            with patch.object(Path,'lstat',side_effect=AssertionError('outside OS access')):
                for value in (str(root.parent/'outside.tif'),'../outside.tif','a/../../outside.tif'):
                    self.assertIsNone(local_file(value,root))
                if os.name=='nt':
                    self.assertIsNone(local_file(r'\\untrusted-host\share\file.tif',root))
                    foreign='Z:' if root.drive.upper()!='Z:' else 'Y:'
                    self.assertIsNone(local_file(foreign+r'\outside.tif',root))

    def test_windows_drive_case_preserved(self):
        if os.name!='nt': self.skipTest('Windows drive semantics')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(); target=root/'file.tif'; target.write_bytes(b'x')
            self.assertEqual(local_file(str(target).swapcase(),root),target)

    def test_missing_directory_nonregular_and_ads_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(); (root/'directory').mkdir(); (root/'regular').write_bytes(b'x')
            for value in ('missing','directory','regular/child','regular:stream','directory/../regular.','regular '):
                self.assertIsNone(local_file(value,root))

    def test_reparse_at_root_parent_or_leaf_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(); (root/'nested').mkdir(); target=root/'nested/file.tif'; target.write_bytes(b'x')
            original=Path.lstat
            for blocked in (root,root/'nested',target):
                def inspect(path,*,_blocked=blocked):
                    info=original(path)
                    return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400) if path==_blocked else info
                with patch.object(Path,'lstat',inspect):
                    self.assertIsNone(local_file('nested/file.tif',root))

    def test_symlink_component_rejected_even_when_target_inside(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(); (root/'nested').mkdir(); target=root/'nested/file.tif'; target.write_bytes(b'x')
            original=Path.lstat
            for blocked in (root/'nested',target):
                def inspect(path,*,_blocked=blocked):
                    return SimpleNamespace(st_mode=stat.S_IFLNK|0o777,st_file_attributes=0) if path==_blocked else original(path)
                with patch.object(Path,'lstat',inspect): self.assertIsNone(local_file('nested/file.tif',root))

if __name__=='__main__': unittest.main()
