"""Config flow for Mastodon."""

from __future__ import annotations

from typing import Any

from mastodon.Mastodon import (
    Account,
    Instance,
    MastodonNetworkError,
    MastodonUnauthorizedError,
)
import voluptuous as vol
from yarl import URL

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import slugify

from .const import CONF_BASE_URL, DOMAIN, LOGGER
from .utils import construct_mastodon_username, create_mastodon_client

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_BASE_URL,
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Required(
            CONF_CLIENT_ID,
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(
            CONF_CLIENT_SECRET,
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(
            CONF_ACCESS_TOKEN,
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
)


def base_url_from_url(url: str) -> str:
    """Return the base url from a url."""
    return str(URL(url).origin())


class MastodonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    def check_connection(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        access_token: str,
    ) -> tuple[
        Instance | None,
        Account | None,
        dict[str, str],
    ]:
        """Check connection to the Mastodon instance."""
        try:
            client = create_mastodon_client(
                base_url,
                client_id,
                client_secret,
                access_token,
            )
            instance = client.instance()
            account = client.account_verify_credentials()

        except MastodonNetworkError:
            return None, None, {"base": "network_error"}
        except MastodonUnauthorizedError:
            return None, None, {"base": "unauthorized_error"}
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected error")
            return None, None, {"base": "unknown"}
        return instance, account, {}

    def show_user_form(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
        description_placeholders: dict[str, str] | None = None,
        step_id: str = "user",
    ) -> ConfigFlowResult:
        """Show the user form."""
        if user_input is None:
            user_input = {}
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            description_placeholders=description_placeholders,
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] | None = None
        if user_input:
            user_input[CONF_BASE_URL] = base_url_from_url(user_input[CONF_BASE_URL])

            instance, account, errors = await self.hass.async_add_executor_job(
                self.check_connection,
                user_input[CONF_BASE_URL],
                user_input[CONF_CLIENT_ID],
                user_input[CONF_CLIENT_SECRET],
                user_input[CONF_ACCESS_TOKEN],
            )

            if not errors:
                name = construct_mastodon_username(instance, account)
                await self.async_set_unique_id(slugify(name))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data=user_input,
                )

        return self.show_user_form(user_input, errors)
