import typer

from wpp import db

app = typer.Typer()


@app.command()
def create_wpp(state: str, force: bool = False):
    db.create_wpp(state, force=force)


@app.command()
def create_pois(state: str, force: bool = False):
    db.create_pois(state, force=force)


@app.command()
def create_state_boundaries(state: str, force: bool = False):
    db.create_state_boundaries(state, force=force)


@app.command()
def build_state(state: str, force: bool = False):
    db.build_state(state, force=force)


@app.command()
def create_block_group_poi_visits(state: str, force: bool = False):
    db.create_block_group_poi_visits(state, force=force)


@app.command()
def build_all(force: bool = False):
    db.build_all(force=force)


if __name__ == "__main__":
    app()
