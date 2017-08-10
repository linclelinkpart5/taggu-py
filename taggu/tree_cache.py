# import collections
# import pathlib as pl
#
# import taggu.types as tt
#
#
# class TreeCache(collections.defaultdict):
#     def __init__(self):
#         # Autovivication at its finest.
#         super().__init__(TreeCache)
#         self.metadata: tt.Metadata = {}
#
#     def path(self, p: pl.Path) -> 'TreeCache':
#         node = self
#         for part in p.parts:
#             node = node[part]
#
#         return node
#
#     def has_path(self, p: pl.Path) -> bool:
#         node = self
#         for part in p.parts:
#             if part not in node:
#                 return False
#             node = node[part]
#
#         return True
