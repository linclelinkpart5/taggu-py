import click


class ArgNames:
    LIBRARY_ROOT_DIR = 'library-root-dir'
    FILE_FN = 'file-fn'
    SELF_FN = 'self-fn'


@click.group()
@click.argument(f'{ArgNames.LIBRARY_ROOT_DIR}', type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
@click.option(f'--{ArgNames.FILE_FN}', default='taggu_file.yml')
@click.option(f'--{ArgNames.SELF_FN}', default='taggu_self.yml')
@click.pass_context
def cli(ctx, library_root_dir, file_fn, self_fn):
    ctx.obj[ArgNames.LIBRARY_ROOT_DIR] = library_root_dir
    ctx.obj[ArgNames.FILE_FN] = file_fn
    ctx.obj[ArgNames.SELF_FN] = self_fn


@cli.command()
@click.pass_context
def interactive(ctx):
    click.echo('Interactive mode!')
    click.echo(f'Library Root Dir: {ctx.obj[ArgNames.LIBRARY_ROOT_DIR]}, '
               f'File FN: {ctx.obj[ArgNames.FILE_FN]}, '
               f'Self FN: {ctx.obj[ArgNames.SELF_FN]}')


@cli.command()
@click.pass_context
def query(ctx):
    click.echo('Query mode!')
    click.echo(f'Library Root Dir: {ctx.obj[ArgNames.LIBRARY_ROOT_DIR]}, '
               f'File FN: {ctx.obj[ArgNames.FILE_FN]}, '
               f'Self FN: {ctx.obj[ArgNames.SELF_FN]}')
