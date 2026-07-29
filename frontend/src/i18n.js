import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      appName: "TeachHub",
      tagline: "Interactive teaching, ready to play.",
      nav: { feed: "Feed", publish: "Publish", profile: "Profile", admin: "Admin", login: "Log in", register: "Sign up", logout: "Log out" },
      search: { placeholder: "Search assignments by title...", subject: "Subject", grade: "Grade", all: "All", clear: "Clear filters", results: "assignments found" },
      subjects: { mathematics: "Mathematics", physics: "Physics", chemistry: "Chemistry", literature: "Literature", history: "History", foreign_languages: "Foreign Languages", other: "Other" },
      grades: { "1-4": "Grades 1-4", "5-6": "Grades 5-6", "7-8": "Grades 7-8", "9-11": "Grades 9-11", university: "University" },
      card: { views: "views", by: "by", open: "Open" },
      feed: { title: "Explore Assignments", subtitle: "Browse and run interactive lessons instantly — no account needed.", empty: "No assignments match your search.", emptyPublish: "Be the first to publish one!" },
      view: { runIt: "Interactive Player", like: "Like", liked: "Liked", favorite: "Favorite", favorited: "Favorited", report: "Report", edit: "Edit", delete: "Delete", back: "Back to feed", loginToInteract: "Log in to like, favorite or report.", deleteConfirm: "Delete this assignment? This cannot be undone.", views: "views", published: "Published", fullscreen: "Fullscreen" },
      publish: { titleNew: "Publish Assignment", titleEdit: "Edit Assignment", formTitle: "Title", subject: "Subject", grade: "Grade", description: "Description", descHint: "Max 500 characters", tags: "Tags (comma separated)", html: "HTML Code", htmlHint: "Paste your interactive HTML. Runs sandboxed. Max 1 MB.", preview: "Live Preview", previewEmpty: "Your HTML preview will appear here.", submit: "Publish", update: "Save changes", cancel: "Cancel", success: "Assignment published!", updated: "Assignment updated!", selectSubject: "Select subject", selectGrade: "Select grade" },
      auth: { loginTitle: "Welcome back", registerTitle: "Create your teacher account", email: "Email", password: "Password", name: "Full name", loginBtn: "Log in", registerBtn: "Sign up", noAccount: "No account?", haveAccount: "Already have an account?", passwordHint: "At least 8 characters", loginSuccess: "Logged in!", registerSuccess: "Account created!" },
      profile: { title: "My Profile", myTasks: "My Assignments", favorites: "Favorites", settings: "Settings", noTasks: "You haven't published anything yet.", noFavorites: "No favorites yet.", changeName: "Display name", changeEmail: "Email", saveAccount: "Save account", currentPassword: "Current password", newPassword: "New password", changePassword: "Change password", dangerZone: "Danger zone", deleteAccount: "Delete account", deleteConfirm: "Permanently delete your account and all your assignments?", saved: "Saved!", passwordChanged: "Password changed!", accountDeleted: "Account deleted." },
      admin: { title: "Admin Dashboard", users: "Users", reports: "Reports", stats: { users: "Users", tasks: "Assignments", reports: "Reports" }, userName: "Name", userEmail: "Email", userRole: "Role", userTasks: "Assignments", actions: "Actions", noReports: "No reports. Everything looks clean!", reportedTask: "Assignment", reason: "Reason", reporter: "Reporter", dismiss: "Dismiss", deleteTask: "Delete assignment", deleteUser: "Delete user", deleteUserConfirm: "Delete this user and all their content?" },
      report: { title: "Report assignment", reason: "Why are you reporting this?", submit: "Submit report", success: "Report submitted. Thank you." },
      common: { loading: "Loading...", error: "Something went wrong.", page: "Page", of: "of", prev: "Previous", next: "Next", cancel: "Cancel", confirm: "Confirm", save: "Save" },
    },
  },
  ru: {
    translation: {
      appName: "TeachHub",
      tagline: "Интерактивное обучение, готовое к запуску.",
      nav: { feed: "Лента", publish: "Опубликовать", profile: "Профиль", admin: "Админ", login: "Войти", register: "Регистрация", logout: "Выйти" },
      search: { placeholder: "Поиск заданий по названию...", subject: "Предмет", grade: "Класс", all: "Все", clear: "Сбросить фильтры", results: "заданий найдено" },
      subjects: { mathematics: "Математика", physics: "Физика", chemistry: "Химия", literature: "Литература", history: "История", foreign_languages: "Иностранные языки", other: "Другое" },
      grades: { "1-4": "1-4 классы", "5-6": "5-6 классы", "7-8": "7-8 классы", "9-11": "9-11 классы", university: "Университет" },
      card: { views: "просмотров", by: "автор", open: "Открыть" },
      feed: { title: "Каталог заданий", subtitle: "Просматривайте и запускайте интерактивные уроки мгновенно — без регистрации.", empty: "Нет заданий по вашему запросу.", emptyPublish: "Опубликуйте первое задание!" },
      view: { runIt: "Интерактивный плеер", like: "Нравится", liked: "Нравится", favorite: "В избранное", favorited: "В избранном", report: "Пожаловаться", edit: "Редактировать", delete: "Удалить", back: "Назад к ленте", loginToInteract: "Войдите, чтобы ставить лайки и добавлять в избранное.", deleteConfirm: "Удалить это задание? Это действие необратимо.", views: "просмотров", published: "Опубликовано", fullscreen: "На весь экран" },
      publish: { titleNew: "Опубликовать задание", titleEdit: "Редактировать задание", formTitle: "Название", subject: "Предмет", grade: "Класс", description: "Описание", descHint: "Максимум 500 символов", tags: "Теги (через запятую)", html: "HTML-код", htmlHint: "Вставьте интерактивный HTML. Запускается в песочнице. Максимум 1 МБ.", preview: "Предпросмотр", previewEmpty: "Здесь появится предпросмотр вашего HTML.", submit: "Опубликовать", update: "Сохранить", cancel: "Отмена", success: "Задание опубликовано!", updated: "Задание обновлено!", selectSubject: "Выберите предмет", selectGrade: "Выберите класс" },
      auth: { loginTitle: "С возвращением", registerTitle: "Создайте аккаунт преподавателя", email: "Эл. почта", password: "Пароль", name: "Полное имя", loginBtn: "Войти", registerBtn: "Зарегистрироваться", noAccount: "Нет аккаунта?", haveAccount: "Уже есть аккаунт?", passwordHint: "Минимум 8 символов", loginSuccess: "Вы вошли!", registerSuccess: "Аккаунт создан!" },
      profile: { title: "Мой профиль", myTasks: "Мои задания", favorites: "Избранное", settings: "Настройки", noTasks: "Вы ещё ничего не опубликовали.", noFavorites: "Пока нет избранного.", changeName: "Отображаемое имя", changeEmail: "Эл. почта", saveAccount: "Сохранить", currentPassword: "Текущий пароль", newPassword: "Новый пароль", changePassword: "Сменить пароль", dangerZone: "Опасная зона", deleteAccount: "Удалить аккаунт", deleteConfirm: "Навсегда удалить аккаунт и все ваши задания?", saved: "Сохранено!", passwordChanged: "Пароль изменён!", accountDeleted: "Аккаунт удалён." },
      admin: { title: "Панель администратора", users: "Пользователи", reports: "Жалобы", stats: { users: "Пользователи", tasks: "Задания", reports: "Жалобы" }, userName: "Имя", userEmail: "Эл. почта", userRole: "Роль", userTasks: "Задания", actions: "Действия", noReports: "Жалоб нет. Всё чисто!", reportedTask: "Задание", reason: "Причина", reporter: "Заявитель", dismiss: "Отклонить", deleteTask: "Удалить задание", deleteUser: "Удалить пользователя", deleteUserConfirm: "Удалить пользователя и весь его контент?" },
      report: { title: "Пожаловаться на задание", reason: "Почему вы жалуетесь?", submit: "Отправить жалобу", success: "Жалоба отправлена. Спасибо." },
      common: { loading: "Загрузка...", error: "Что-то пошло не так.", page: "Страница", of: "из", prev: "Назад", next: "Далее", cancel: "Отмена", confirm: "Подтвердить", save: "Сохранить" },
    },
  },
};

const stored = typeof window !== "undefined" ? localStorage.getItem("th_lang") : null;
const browser = typeof navigator !== "undefined" && navigator.language && navigator.language.startsWith("ru") ? "ru" : "en";

i18n.use(initReactI18next).init({
  resources,
  lng: stored || browser,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
