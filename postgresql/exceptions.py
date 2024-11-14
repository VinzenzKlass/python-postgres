class PGError(Exception):
    def __init__(self):
        super().__init__("Postgres Error.")
