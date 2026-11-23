import pickle
from collections import UserDict
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable


class Field:
    """Базовий клас для полів запису."""

    def __init__(self, value):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class Name(Field):
    """Клас для зберігання імені контакту. Обов'язкове поле."""

    def __init__(self, value: str):
        if not value or not value.strip():
            raise ValueError("Contact name cannot be empty.")
        super().__init__(value.strip())


class Phone(Field):
    """Клас для зберігання номера телефону з валідацією (рівно 10 цифр)."""

    def __init__(self, value: str):
        if not self._is_valid(value):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)

    @staticmethod
    def _is_valid(value: str) -> bool:
        return isinstance(value, str) and value.isdigit() and len(value) == 10


class Birthday(Field):
    """Клас для зберігання дати народження у форматі DD.MM.YYYY."""

    def __init__(self, value: str):
        try:
            parsed_date = datetime.strptime(value, "%d.%m.%Y").date()
            super().__init__(parsed_date)
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

    def __str__(self) -> str:
        return self.value.strftime("%d.%m.%Y")


class Record:
    """Клас для зберігання інформації про контакт: ім'я, телефони та день народження."""

    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.birthday: Birthday | None = None

    def add_phone(self, phone_number: str) -> None:
        """Додає новий номер телефону до запису (якщо такого ще немає)."""
        if self.find_phone(phone_number) is None:
            self.phones.append(Phone(phone_number))

    def remove_phone(self, phone_number: str) -> None:
        """Видаляє номер телефону із запису."""
        phone_obj = self.find_phone(phone_number)
        if phone_obj is None:
            raise ValueError(f"Phone number {phone_number} not found.")
        self.phones.remove(phone_obj)

    def edit_phone(self, old_phone: str, new_phone: str) -> None:
        """Редагує існуючий номер телефону."""
        phone_obj = self.find_phone(old_phone)
        if phone_obj is None:
            raise ValueError(f"Phone number {old_phone} not found.")
        validated_new_phone = Phone(new_phone)
        phone_obj.value = validated_new_phone.value

    def find_phone(self, phone_number: str) -> Phone | None:
        """Шукає об'єкт Phone за значенням номера."""
        for phone in self.phones:
            if phone.value == phone_number:
                return phone
        return None

    def add_birthday(self, birthday: str) -> None:
        """Додає або оновлює дату народження контакту."""
        self.birthday = Birthday(birthday)

    def __str__(self) -> str:
        phones_str = "; ".join(p.value for p in self.phones) if self.phones else "no phones"
        birthday_str = f", birthday: {self.birthday}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones_str}{birthday_str}"


class AddressBook(UserDict):
    """Клас для зберігання записів та керування адресною книгою."""

    def add_record(self, record: Record) -> None:
        """Додає запис до адресної книги."""
        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        """Знаходить запис за ім'ям."""
        return self.data.get(name)

    def delete(self, name: str) -> None:
        """Видаляє запис за ім'ям."""
        if name in self.data:
            del self.data[name]

    def get_upcoming_birthdays(self) -> list[dict[str, str]]:
        """
        Повертає список словників із іменами та датами привітання для контактів,
        у яких день народження відбудеться протягом наступних 7 днів (включно із сьогодні).
        Якщо день народження припадає на вихідний, привітання переноситься на понеділок.
        """
        today = datetime.today().date()
        upcoming_birthdays = []

        for record in self.data.values():
            if record.birthday is None:
                continue

            bday = record.birthday.value

            # Обробка 29 лютого у невисокосний рік
            try:
                birthday_this_year = bday.replace(year=today.year)
            except ValueError:
                birthday_this_year = bday.replace(year=today.year, day=28)

            # Якщо день народження цього року вже минув — перевіряємо наступний рік
            if birthday_this_year < today:
                try:
                    birthday_this_year = bday.replace(year=today.year + 1)
                except ValueError:
                    birthday_this_year = bday.replace(year=today.year + 1, day=28)

            days_until = (birthday_this_year - today).days

            if 0 <= days_until <= 7:
                congratulation_date = birthday_this_year
                # 5 — субота, 6 — неділя
                if congratulation_date.weekday() == 5:
                    congratulation_date += timedelta(days=2)
                elif congratulation_date.weekday() == 6:
                    congratulation_date += timedelta(days=1)

                upcoming_birthdays.append({
                    "name": record.name.value,
                    "congratulation_date": congratulation_date.strftime("%d.%m.%Y"),
                })

        return upcoming_birthdays


# --- Серіалізація та десеріалізація адресної книги ---

def save_data(book: AddressBook, filename: str = "addressbook.pkl") -> None:
    """Зберігає об'єкт адресної книги у бінарний файл за допомогою pickle."""
    with open(filename, "wb") as f:
        pickle.dump(book, f)


def load_data(filename: str = "addressbook.pkl") -> AddressBook:
    """Завантажує адресну книгу з файлу або створює нову, якщо файл не знайдено."""
    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError, pickle.UnpicklingError):
        return AddressBook()


# --- Декоратор та парсер команд ---

def input_error(func: Callable) -> Callable:
    """Декоратор для обробки помилок введення користувача."""

    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return str(e) if str(e) else "Invalid arguments provided."
        except IndexError:
            return "Enter the argument for the command."
        except KeyError:
            return "Contact not found."

    return inner


def parse_input(user_input: str) -> tuple[str, ...]:
    """Розбирає введений рядок на команду (у нижньому регістрі) та аргументи."""
    parts = user_input.strip().split()
    if not parts:
        return ("",)
    cmd, *args = parts
    return cmd.lower(), *args


# --- Функції-обробники команд (handlers) ---

@input_error
def add_contact(args: list[str], book: AddressBook) -> str:
    """Додає новий контакт або новий номер до існуючого контакту."""
    if len(args) < 2:
        raise ValueError("Give me name and phone please.")
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_contact(args: list[str], book: AddressBook) -> str:
    """Змінює старий номер телефону контакту на новий."""
    if len(args) < 3:
        raise ValueError("Give me name, old phone and new phone please.")
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error
def show_phone(args: list[str], book: AddressBook) -> str:
    """Показує всі номери телефону вказаного контакту."""
    if not args:
        raise IndexError
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return f"Contact {name} has no phones saved."
    return "; ".join(p.value for p in record.phones)


@input_error
def show_all(book: AddressBook) -> str:
    """Виводить усі записи з адресної книги."""
    if not book.data:
        return "Address book is empty."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args: list[str], book: AddressBook) -> str:
    """Додає дату народження до вказаного контакту."""
    if len(args) < 2:
        raise ValueError("Give me name and birthday (DD.MM.YYYY) please.")
    name, birthday_str, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.add_birthday(birthday_str)
    return "Birthday added."


@input_error
def show_birthday(args: list[str], book: AddressBook) -> str:
    """Показує дату народження вказаного контакту."""
    if not args:
        raise IndexError
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError
    if record.birthday is None:
        return f"Birthday for {name} is not set."
    return str(record.birthday)


@input_error
def birthdays(args: list[str], book: AddressBook) -> str:
    """Показує список користувачів, яких потрібно привітати протягом наступного тижня."""
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays in the next 7 days."
    return "\n".join(
        f"{item['name']}: {item['congratulation_date']}" for item in upcoming
    )


# --- Головний цикл бота ---

def main() -> None:
    book = load_data()
    print("Welcome to the assistant bot!")

    try:
        while True:
            user_input = input("Enter a command: ")
            command, *args = parse_input(user_input)

            if command in ["close", "exit"]:
                print("Good bye!")
                break
            elif command == "hello":
                print("How can I help you?")
            elif command == "add":
                print(add_contact(args, book))
            elif command == "change":
                print(change_contact(args, book))
            elif command == "phone":
                print(show_phone(args, book))
            elif command == "all":
                print(show_all(book))
            elif command == "add-birthday":
                print(add_birthday(args, book))
            elif command == "show-birthday":
                print(show_birthday(args, book))
            elif command == "birthdays":
                print(birthdays(args, book))
            else:
                print("Invalid command.")
    finally:
        # Гарантоване збереження даних навіть при екстреному закритті (Ctrl+C)
        save_data(book)


if __name__ == "__main__":
    main()
