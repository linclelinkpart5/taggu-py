import argparse
import pathlib


class Cli:
    @staticmethod
    def as_directory(path_str: str) -> pathlib.Path:
        path = pathlib.Path(path_str)

        if not path.exists() or path.is_dir():
            raise argparse.ArgumentTypeError(f'{path} does not exist or is not a directory')

        return path

    @staticmethod
    def get_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="View Taggu metadata")

        common = argparse.ArgumentParser(add_help=False)
        common.add_argument(
                'library_root_dir',
                type=pathlib.Path,
                help='root directory of music library',
        )

        subparsers = parser.add_subparsers(dest='subcommand')
        # As seen on http://stackoverflow.com/questions/18282403/argparse-with-required-subcommands
        subparsers.required = True

        subparser_interactive = subparsers.add_parser('interactive', parents=[common])
        subparser_query = subparsers.add_parser('query', parents=[common])

        return parser
