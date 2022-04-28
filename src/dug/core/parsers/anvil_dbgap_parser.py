from .dbgap_parser import DbGaPParser


class AnvilDbGaPParser(DbGaPParser):
    def _get_element_type(self):
        return "Anvil"
