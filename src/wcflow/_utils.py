import aiida.orm


class OrmUtils:
    @staticmethod
    def convert_to_class(type_: str) -> aiida.orm.utils.node.AbstractNodeMeta:
        if type_ == "file":
            return aiida.orm.SinglefileData
        elif type_ == "dir":
            return aiida.orm.FolderData
        elif type_ == "int":
            return aiida.orm.Int
        elif type_ == "float":
            return aiida.orm.Float
        else:
            raise ValueError(f"Type {type_} is unknown.")

