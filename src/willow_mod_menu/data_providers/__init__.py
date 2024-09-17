from abc import ABC, abstractmethod

from unrealsdk.unreal import UObject

# Copying these from the real menus
BACK_EVENT_ID = -1
KEYBINDS_EVENT_ID = 1000
RESET_KEYBINDS_EVENT_ID = 1001

# Putting all our options past this point
OPTION_EVENT_ID_OFFSET = 2000

KB_TAG_KEYBIND = "willow_mod_menu:keybind"
KB_TAG_UNREBINDABLE = "willow_mod_menu:unrebindable"
KB_TAG_HEADER = "willow_mod_menu:header"


class DataProvider(ABC):
    @abstractmethod
    def populate(self, data_provider: UObject, the_list: UObject) -> None:
        """
        Populates the list with the appropriate contents.

        Args:
            data_provider: The WillowScrollingListDataProviderOptionsBase to populate with.
            the_list: The WillowScrollingList to populate.
        """
        raise NotImplementedError

    @abstractmethod
    def populate_keybind_keys(self, data_provider: UObject) -> None:
        """
        Fills the data provider's ControllerMappingClip with the current key set for each bind.

        Args:
            data_provider: The WillowScrollingListDataProviderOptionsBase to add keys to.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_click(self, event_id: int, the_list: UObject) -> bool:
        """
        Handles a click on one of the options menu entries.

        Args:
            event_id: The id of the menu entry which was clicked.
            the_list: The WillowScrollingList which was clicked.
        Returns:
            True if the click was handled.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_spinner_change(self, event_id: int, new_choice_idx: int) -> bool:
        """
        Handles one of options menu spinners being changed.

        Args:
            event_id: The id of the spinner which was clicked.
            new_choice_idx: The index of the newly selected choice.
        Returns:
            True if the change was handled.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_slider_change(self, event_id: int, new_value: int) -> bool:
        """
        Handles one of options menu sliders being changed.

        Args:
            event_id: The id of the spinner which was clicked.
            new_value: The new value the spinner got set to.
        Returns:
            True if the change was handled.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_key_rebind(self, data_provider: UObject, key: str) -> None:
        """
        Handles attempting to rebind a key.

        Args:
            data_provider: The WillowScrollingListDataProviderOptionsBase to rebind on.
            key: The key which was input during the rebind menu.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_reset_keybinds(self) -> None:
        """Handles resetting the keybinds associated with this menu."""
        raise NotImplementedError
