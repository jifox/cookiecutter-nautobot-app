"""Nautobot development configuration file."""
import os
import secrets
import sys

from nautobot.core.settings import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import
from nautobot.core.settings_funcs import is_truthy, parse_redis_connection

DJANGO_ALLOW_CIDR_ENABLED = is_truthy(os.getenv("NAUTOBOT_DJANGO_ALLOW_CIDR_ENABLED", False))
if DJANGO_ALLOW_CIDR_ENABLED:
    from allow_cidr import middleware  # noqa F401,F403 # type: ignore

#
# Debug
#

DEBUG = is_truthy(os.getenv("NAUTOBOT_DEBUG", False))
_TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if DEBUG and not _TESTING:
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: True}

    if "debug_toolbar" not in INSTALLED_APPS:  # noqa: F405
        INSTALLED_APPS.append("debug_toolbar")  # noqa: F405
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:  # noqa: F405
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

#
# Misc. settings
#

# This is a list of valid fully-qualified domain names (FQDNs) for the Nautobot server. Nautobot will not permit write
# access to the server via any other hostnames. The first FQDN in the list will be treated as the preferred name.
#
# Example: ALLOWED_HOSTS = ['nautobot.example.com', 'nautobot.internal.local']
ALLOWED_HOSTS = os.getenv("NAUTOBOT_ALLOWED_HOSTS", "").replace(",", " ").split(" ")


#
# Django Middleware Settings
#

ALLOWED_CIDR_NETS = []

if DJANGO_ALLOW_CIDR_ENABLED:
    if "allow_cidr.middleware.AllowCIDRMiddleware" not in MIDDLEWARE:
        MIDDLEWARE.insert(0, "allow_cidr.middleware.AllowCIDRMiddleware")

    if os.getenv("NAUTOBOT_ALLOWED_CIDR_NETS", None):
        ALLOWED_CIDR_NETS = os.getenv("NAUTOBOT_ALLOWED_CIDR_NETS", "").split(",")
    else:
        print("WARNING: No CIDR networks defined in NAUTOBOT_ALLOWED_CIDR_NETS environment variable.")


SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY", "")

#
# Database
#

nautobot_db_engine = os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.postgresql")
default_db_settings = {
    "django.db.backends.postgresql": {
        "NAUTOBOT_DB_PORT": "5432",
    },
    "django.db.backends.mysql": {
        "NAUTOBOT_DB_PORT": "3306",
    },
}
DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),  # Database username
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),  # Database password
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),  # Database server
        "PORT": os.getenv(
            "NAUTOBOT_DB_PORT", default_db_settings[nautobot_db_engine]["NAUTOBOT_DB_PORT"]
        ),  # Database port, default to postgres
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", 300)),  # Database timeout
        "ENGINE": nautobot_db_engine,
    }
}

# Ensure proper Unicode handling for MySQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}

#
# Redis
#

# The django-redis cache is used to establish concurrent locks using Redis.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": parse_redis_connection(redis_database=0),
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

#
# Celery settings are not defined here because they can be overloaded with
# environment variables. By default they use `CACHES["default"]["LOCATION"]`.
#

#
# Credentials that Nautobot will use to authenticate to devices when connecting
# via NAPALM.
#

NAPALM_USERNAME = os.getenv("NAUTOBOT_NAPALM_USERNAME", "")
NAPALM_PASSWORD = os.getenv("NAUTOBOT_NAPALM_PASSWORD", "")
NAPALM_SECRET = os.getenv("NAUTOBOT_NAPALM_SECRET", NAPALM_PASSWORD)
# NAPALM timeout (in seconds). (Default: 30)
NAPALM_TIMEOUT = int(os.getenv("NAUTOBOT_NAPALM_TIMEOUT", 30))


#
# Logging
#

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

# Verbose logging during normal development operation, but quiet logging during unit test execution
if not _TESTING:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "normal": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s : %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() : %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "normal_console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "normal",
            },
            "verbose_console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "loggers": {
            "django": {"handlers": ["normal_console"], "level": "INFO"},
            "nautobot": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            },
        },
    }


# Timezone used for UI ony. Doesn't change the database timezone.
TIME_ZONE = os.getenv("NAUTOBOT_DISPLAY_TIME_ZONE", "Europe/Vienna")

# Date/time formatting. See the following link for supported formats:
# https://docs.djangoproject.com/en/stable/ref/templates/builtins/#date
# Timezone used for UI ony. Doesn't change the database timezone.
DATE_FORMAT = os.getenv("NAUTOBOT_DATE_FORMAT", "N j, Y")
SHORT_DATE_FORMAT = os.getenv("NAUTOBOT_SHORT_DATE_FORMAT", "d.m.Y")
TIME_FORMAT = os.getenv("NAUTOBOT_TIME_FORMAT", "g:i a")
SHORT_TIME_FORMAT = os.getenv("NAUTOBOT_SHORT_TIME_FORMAT", "H:i:s")
DATETIME_FORMAT = os.getenv("NAUTOBOT_DATETIME_FORMAT", "N j, Y g:i a")
SHORT_DATETIME_FORMAT = os.getenv("NAUTOBOT_SHORT_DATETIME_FORMAT", "d.m.Y H:i")

# Initialize or update PLUGINS and PLUGINS_CONFIG settings.
# Take into account that PLUGINS and PLUGINS_CONFIG may be defined elsewhere
if "PLUGINS" not in locals():
    PLUGINS = []
if "PLUGINS_CONFIG" not in locals():
    PLUGINS_CONFIG = {}


#
# App: {{ cookiecutter.verbose_name }}
#
{{ cookiecutter.app_name | upper }}_ENABLED = is_truthy(os.getenv("NAUTOBOT_{{ cookiecutter.app_name | upper }}_ENABLED", False))
if {{ cookiecutter.app_name | upper }}_ENABLED:
    if "{{ cookiecutter.app_name }}" not in PLUGINS:
        # Enable installed plugins. Add the name of each plugin to the list.
        PLUGINS.append("{{ cookiecutter.app_name }}")

    if "{{ cookiecutter.app_name }}" not in PLUGINS_CONFIG:
        # Plugins configuration settings. These settings are used by various plugins that the user may have installed.
        # Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
        PLUGINS_CONFIG.update(
            {
                "{{ cookiecutter.app_name }}": {
                }
            }
        )
        # Apps configuration settings. These settings are used by various Apps that the user may have installed.
        # Each key in the dictionary is the name of an installed App and its value is a dictionary of settings.
        # PLUGINS_CONFIG = {
        #     '{{ cookiecutter.app_name }}': {
        #         'foo': 'bar',
        #         'buzz': 'bazz'
        #     }
        # }

    if "{{ cookiecutter.app_name }}" not in LOGGING.get("loggers"):  # type: ignore
        {{ cookiecutter.app_name }}_logger = {
            "{{ cookiecutter.app_name }}": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            }
        }
        LOGGING.get("loggers").update({{ cookiecutter.app_name }}_logger)  # type: ignore


#
# App: Data Validation Engine
#
# see: https://docs.nautobot.com/projects/data-validation/en/latest/admin/install/#install-guide
#

DATA_VALIDATION_ENGINE_ENABLED = is_truthy(os.getenv("NAUTOBOT_DATA_VALIDATION_ENGINE_ENABLED", False))
if DATA_VALIDATION_ENGINE_ENABLED:
    if "nautobot_data_validation_engine" not in PLUGINS_CONFIG:  # type: ignore
        # Enable installed plugins. Add the name of each plugin to the list.
        PLUGINS.append("nautobot_data_validation_engine")

    if "nautobot_data_validation_engine" not in PLUGINS_CONFIG:  # type: ignore
        # Plugins configuration settings. These settings are used by various plugins that the user may have installed.
        # Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
        PLUGINS_CONFIG.update(  # type: ignore
            {
                "nautobot_data_validation_engine": {},
            }
        )


#
# App: Device Onboarding
#
# see: https://docs.nautobot.com/projects/device-onboarding/en/latest/admin/install/
#

DEVICE_ONBOARDING_ENABLED = is_truthy(os.getenv("NAUTOBOT_DEVICE_ONBOARDING_ENABLED", False))
if DEVICE_ONBOARDING_ENABLED:
    if "nautobot_device_onboarding" not in PLUGINS:
        # Enable installed plugins. Add the name of each plugin to the list.
        PLUGINS.append("nautobot_device_onboarding")

    if "nautobot_device_onboarding" not in PLUGINS_CONFIG:  # type: ignore
        # Plugins configuration settings. These settings are used by various plugins that the user may have installed.
        # Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
        PLUGINS_CONFIG.update(  # type: ignore
            {
                "nautobot_device_onboarding": {
                    "default_device_role_color": "0000FF",
                    "default_device_role": "edge-switch",
                    "skip_device_type_on_update": True,
                    # "platform_map": {
                    #     <Netmiko Platform>: <Nautobot Slug>
                    # },
                },
            }
        )


#
# App: Django Auth LDAP
#
# see: https://nautobot.readthedocs.io/en/latest/configuration/authentication/ldap/
#

DJANGO_AUTH_LDAP_ENABLED = is_truthy(os.getenv("NAUTOBOT_DJANGO_AUTH_LDAP_ENABLED", False))

# Server URI
# When using Windows Server 2012 you may need to specify a port on
# AUTH_LDAP_SERVER_URI. Use 3269 for secure, or 3268 for non-secure.
AUTH_LDAP_SERVER_URI = os.getenv("NAUTOBOT_AUTH_LDAP_SERVER_URI", None)

if DJANGO_AUTH_LDAP_ENABLED and AUTH_LDAP_SERVER_URI:
    import ldap  # type:ignore

    from django_auth_ldap.config import (  # type:ignore
        LDAPSearch,
        GroupOfNamesType,
        LDAPSearchUnion,
    )

    ldap_logger = {
        "django_auth_ldap": {
            "handlers": ["normal_console"],
            "level": LOG_LEVEL,
        },
    }
    LOGGING.get("loggers").update(ldap_logger)  # type: ignore

    AUTHENTICATION_BACKENDS = [
        "django_auth_ldap.backend.LDAPBackend",
        "nautobot.core.authentication.ObjectPermissionBackend",
    ]

    # The following may be needed if you are binding to Active Directory.
    AUTH_LDAP_CONNECTION_OPTIONS = {ldap.OPT_REFERRALS: 0}  # type: ignore

    # Set the DN and password for the Nautobot service account.
    AUTH_LDAP_BIND_DN = os.getenv("NAUTOBOT_AUTH_LDAP_BIND_DN")
    AUTH_LDAP_BIND_PASSWORD = os.getenv("NAUTOBOT_AUTH_LDAP_BIND_PASSWORD")

    # Include this `ldap.set_option` call if you want to ignore certificate errors.
    # This might be needed to accept a self-signed cert.
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)  # type: ignore

    #
    # LDAP User Authentication
    #

    # Base DN to search for user groups
    AUTH_LDAP_GROUP_SEARCH = os.getenv("NAUTOBOT_AUTH_LDAP_GROUP_SEARCH", None)

    # This search matches users with the sAMAccountName equal to the provided username.
    # This is required if the user's username is not in their DN (Active Directory).
    AUTH_LDAP_USER_SEARCH_DN = os.getenv("NAUTOBOT_AUTH_LDAP_USER_SEARCH_DN", None)

    # This search matches users with the sAMAccountName equal to the provided username.
    if AUTH_LDAP_USER_SEARCH_DN:
        user_search_dn_list = str(AUTH_LDAP_USER_SEARCH_DN).split(";")
        lds = []
        for sdn in user_search_dn_list:
            lds.append(LDAPSearch(sdn.strip(), ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"))  # type: ignore
        AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(*lds)
    else:
        AUTH_LDAP_USER_SEARCH = None

    # You can map user attributes to Django attributes as so.
    AUTH_LDAP_USER_ATTR_MAP = {
        # "username": "sAMAccountName",
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    }

    #
    # LDAP User Groups for Permissions
    #

    # If a user's DN is producible from their username, we don't need to search.
    # AUTH_LDAP_USER_DN_TEMPLATE = "uid=%(user)s,ou=users,dc=example,dc=com"

    # This search ought to return all groups to which the user belongs.
    # django_auth_ldap uses this to determine group hierarchy.
    # AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr="cn")
    # AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType()
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()

    # All users must be mapped to at least this group to enable authentication.
    # Without this, users cannot log in.
    AUTH_LDAP_REQUIRE_GROUP = os.getenv("NAUTOBOT_AUTH_LDAP_REQUIRE_GROUP")

    # Users mapped to this group are enabled for access to the administration tools;
    # this is the equivalent of checking the "staff status" box on a manually created user.
    # This doesn't grant any specific permissions.
    AUTH_LDAP_USER_IS_STUFF_GROUP = os.getenv("NAUTOBOT_AUTH_LDAP_USER_IS_STUFF_GROUP")

    # Users mapped to this group will be granted superuser status.
    # Superusers are implicitly granted all permissions.
    AUTH_LDAP_USER_IS_SUPERUSER_GROUP = os.getenv("NAUTOBOT_AUTH_LDAP_USER_IS_SUPERUSER_GROUP")

    # Assign new users to default group
    EXTERNAL_AUTH_DEFAULT_GROUPS = []
    EXTERNAL_AUTH_DEFAULT_GROUP_NAMES = os.getenv("NAUTOBOT_EXTERNAL_AUTH_DEFAULT_GROUPS", "")
    if EXTERNAL_AUTH_DEFAULT_GROUP_NAMES:
        for gnam in EXTERNAL_AUTH_DEFAULT_GROUP_NAMES.split(","):
            EXTERNAL_AUTH_DEFAULT_GROUPS.append(gnam.strip())

    # Use LDAP group membership to calculate group permissions.
    # AUTH_LDAP_FIND_GROUP_PERMS = True

    # Define special user types using groups. Exercise great caution when assigning superuser status.
    #   is_active -  All users must be mapped to at least this group to enable
    #                authentication. Without this, users cannot log in.
    #   is_staff -   Users mapped to this group are enabled for access to the
    #                administration tools; this is the equivalent of checking the "staff status"
    #                box on a manually created user. This doesn't grant any specific permissions.
    #   is_superuser - Users mapped to this group will be granted superuser status. Superusers
    #                are implicitly granted all permissions.
    AUTH_LDAP_USER_FLAGS_BY_GROUP = {
        "is_active": AUTH_LDAP_REQUIRE_GROUP,
        "is_staff": AUTH_LDAP_USER_IS_STUFF_GROUP,
        "is_superuser": AUTH_LDAP_USER_IS_SUPERUSER_GROUP,
    }

    # For more granular permissions, we can map LDAP groups to Django groups.
    AUTH_LDAP_FIND_GROUP_PERMS = False

    # Cache groups for one hour to reduce LDAP traffic
    AUTH_LDAP_CACHE_TIMEOUT = 3600


#
# App: Nautobot-SSOT-Plugin Plugin-Settings
#
# see: https://docs.nautobot.com/projects/ssot/en/latest/admin/install/
#

SSOT_ENABLED = is_truthy(os.getenv("NAUTOBOT_SSOT_ENABLED", False))
if SSOT_ENABLED:
    if "nautobot_ssot" not in PLUGINS:
        PLUGINS.append("nautobot_ssot")

    if "nautobot_ssot" not in PLUGINS_CONFIG:  # type: ignore
        PLUGINS_CONFIG.update({"nautobot_ssot": {"hide_example_jobs": True}})  # type: ignore


#
# App: Nautobot-Device-Onboarding-Plugin Plugin-Settings
#
# see: https://github.com/nautobot/nautobot-plugin-device-onboarding#nautobot-configuration
#

DEVICE_ONBOARDING_ENABLED = is_truthy(os.getenv("NAUTOBOT_DEVICE_ONBOARDING_ENABLED", False))
if DEVICE_ONBOARDING_ENABLED:
    if "nautobot_device_onboarding" not in PLUGINS:
        PLUGINS.append("nautobot_device_onboarding")

    if "nautobot_device_onboarding" not in PLUGINS_CONFIG:  # type: ignore
        PLUGINS_CONFIG.update(  # type: ignore
            {
                "nautobot_device_onboarding": {
                    "default_device_role_color": "0000FF",
                    "default_device_role": "edge-switch",
                    "skip_device_type_on_update": True,
                    "skip_manufacturer_on_update": True,
                },
            }
        )


#
# App: Nautobot Secrets Providers
#
# see: https://github.com/nautobot/nautobot-app-secrets-providers
#

SECRETS_PROVIDERS_ENABLED = is_truthy(os.getenv("NAUTOBOT_SECRETS_PROVIDERS_ENABLED", False))
if SECRETS_PROVIDERS_ENABLED:
    if "nautobot_secrets_providers" not in PLUGINS:
        PLUGINS.append("nautobot_secrets_providers")
        print("INFO: nautobot_secrets_providers plugin enabled.")  # noqa: T001

    if "nautobot_secrets_providers" not in PLUGINS_CONFIG or "thycotic" not in PLUGINS_CONFIG.get(  # type: ignore
        "nautobot_secrets_providers"
    ):  # type: ignore
        thycotic_seetings = {
            "thycotic": {  # https://github.com/thycotic/python-tss-sdk
                "base_url": os.getenv("SECRET_SERVER_BASE_URL"),
                "cloud_based": is_truthy(os.getenv("SECRET_SERVER_IS_CLOUD_BASED", "False")),
                # tenant: required when cloud_based == True
                "tenant": os.getenv("SECRET_SERVER_TENANT", ""),
                # Setup thycotic authorizer
                # Username | Password | Token | Domain | Authorizer
                #   def    |   def    |   *   |   -    | PasswordGrantAuthorizer
                #   def    |   def    |   *   |  def   | DomainPasswordGrantAuthorizer
                #    -     |    -     |  def  |   *    | AccessTokenAuthorizer
                #   def    |    -     |  def  |   *    | AccessTokenAuthorizer
                #    -     |   def    |  def  |   *    | AccessTokenAuthorizer
                "username": os.getenv("SECRET_SERVER_USERNAME", ""),
                "password": os.getenv("SECRET_SERVER_PASSWORD", ""),
                "token": os.getenv("SECRET_SERVER_TOKEN", ""),
                "domain": os.getenv("SECRET_SERVER_DOMAIN", ""),
                # ca_bundle_path: (optional) Path to trusted certificates file.
                #     This must be set as environment variable.
                #     see: https://docs.python-requests.org/en/master/user/advanced/
                "ca_bundle_path": os.getenv("REQUESTS_CA_BUNDLE", ""),
            }
        }

        if "nautobot_secrets_providers" in PLUGINS_CONFIG:  # type: ignore
            PLUGINS_CONFIG.get("nautobot_secrets_providers").update(thycotic_seetings)  # type: ignore
        else:
            PLUGINS_CONFIG.update({"nautobot_secrets_providers": thycotic_seetings})


#
# App:
#
