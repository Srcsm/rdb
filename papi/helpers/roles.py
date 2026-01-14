class RoleHelper:
    @staticmethod
    def parse_allowed_roles(roles_string: str) -> list:
        """Parse the allowed_roles config string into a list of role names/IDs"""
        if not roles_string or roles_string.strip() == "":
            return []
        
        roles = [role.strip() for role in roles_string.split(',')]
        
        parsed_roles = []
        for role in roles:
            if role.isdigit():
                parsed_roles.append(int(role))
            else:
                parsed_roles.append(role)
        
        return parsed_roles