import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      appName: "TeachHub",
      tagline: "Interactive teaching, ready to play.",
      nav: { feed: "Feed", publish: "Publish", profile: "Profile", admin: "Admin", login: "Log in", register: "Sign up", logout: "Log out", workspace: "Studio" },
      search: { placeholder: "Search by title...", subject: "Subject", grade: "Grade", type: "Type", all: "All", clear: "Clear filters", results: "posts found" },
      subjects: { mathematics: "Mathematics", physics: "Physics", chemistry: "Chemistry", literature: "Literature", history: "History", foreign_languages: "Foreign Languages", other: "Other" },
      grades: { "1-4": "Grades 1-4", "5-6": "Grades 5-6", "7-8": "Grades 7-8", "9-11": "Grades 9-11", university: "University" },
      types: { html: "Interactive", worksheet: "Worksheet", blog: "Blog", all: "All types" },
      card: { views: "views", by: "by", open: "Open", download: "Download", readMore: "Read more", files: "files", draft: "Draft" },
      feed: { title: "Explore Posts", subtitle: "Browse and run interactive lessons, worksheets and teacher blogs — no account needed.", empty: "No posts match your search.", emptyPublish: "Be the first to publish one!", exploreTab: "Explore", followingTab: "Following", followingEmpty: "You're not following anyone yet. Follow teachers to see their posts here.", loginForFollowing: "Log in to see posts from teachers you follow." },
      view: { runIt: "Interactive Player", like: "Like", liked: "Liked", favorite: "Favorite", favorited: "Favorited", report: "Report", edit: "Edit", delete: "Delete", back: "Back to feed", loginToInteract: "Log in to like, favorite or report.", deleteConfirm: "Delete this post? This cannot be undone.", views: "views", published: "Published", fullscreen: "Fullscreen", download: "Download", attachments: "Attachments", viewProfile: "View author" },
      publish: {
        titleNew: "Create Post", titleEdit: "Edit Post", chooseType: "What are you publishing?",
        typeHtmlDesc: "Interactive HTML that plays on the site (quiz, game, visualization).",
        typeWorksheetDesc: "Downloadable files — images and documents (PDF, DOCX, XLSX...).",
        typeBlogDesc: "A text + image post to share experiences and tips.",
        formTitle: "Title", subject: "Subject", grade: "Grade", description: "Description", descHint: "Max 500 characters",
        tags: "Tags (comma separated)", html: "HTML Code", htmlHint: "Paste your interactive HTML. Runs sandboxed. Max 1 MB.",
        blogBody: "Post content", blogBodyHint: "Write your article. Add images below.",
        worksheetFiles: "Worksheet files", worksheetHint: "Upload images (PNG/JPG/WebP) and documents (PDF, DOCX, XLSX, PPTX). Max 25MB each.",
        blogImages: "Images (optional)", uploadFile: "Upload file", uploadImage: "Add image", uploading: "Uploading...",
        remove: "Remove", folder: "Folder", noFolder: "No folder",
        preview: "Live Preview", previewEmpty: "Your preview will appear here.", submit: "Publish", update: "Save changes",
        cancel: "Cancel", success: "Post published!", updated: "Post updated!", selectSubject: "Select subject", selectGrade: "Select grade",
        draftLabel: "Save as draft", draftHint: "Only you can see drafts until you publish.", saveDraft: "Save draft",
      },
      auth: { loginTitle: "Welcome back", registerTitle: "Create your teacher account", email: "Email", password: "Password", confirmPassword: "Confirm password", passwordMismatch: "Passwords do not match", name: "Full name", loginBtn: "Log in", registerBtn: "Sign up", noAccount: "No account?", haveAccount: "Already have an account?", passwordHint: "At least 8 characters", loginSuccess: "Logged in!", registerSuccess: "Account created!", show: "Show password", hide: "Hide password" },
      profile: { title: "My Profile", myTasks: "My Posts", favorites: "Favorites", settings: "Settings", followers: "Followers", following: "Following", noTasks: "You haven't published anything yet.", noFavorites: "No favorites yet.", noFollowers: "No followers yet.", noFollowing: "You're not following anyone yet.", changeName: "Display name", changeEmail: "Email", saveAccount: "Save account", currentPassword: "Current password", newPassword: "New password", changePassword: "Change password", dangerZone: "Danger zone", deleteAccount: "Delete account", deleteConfirm: "Permanently delete your account and all your posts?", saved: "Saved!", passwordChanged: "Password changed!", accountDeleted: "Account deleted.", openStudio: "Open Studio", viewProfile: "View public profile", changeAvatar: "Change avatar", bio: "About me", bioHint: "Tell others a bit about yourself (max 500 chars)", hideFollowers: "Hide my followers list", hideFollowing: "Hide my following list", privacy: "Privacy" },
      follow: { follow: "Follow", following: "Following", unfollow: "Unfollow", followers: "Followers", followingList: "Following", posts: "posts", memberSince: "Member since", noPosts: "No posts yet." },
      workspace: { title: "Studio", logoHint: "Back to feed", account: "Account", fullscreen: "Full-screen preview", exit: "Exit full-screen", folders: "Folders", allTasks: "All posts", byType: "By type", bySubject: "By subject", myFolders: "My folders", createFolder: "New folder", folderName: "Folder name", create: "Create", posts: "Posts", noPosts: "No posts here.", selectPost: "Select a post to preview it", edit: "Edit", deleteFolder: "Delete folder", deleteFolderConfirm: "Delete this folder? Posts inside will be moved out of the folder (not deleted).", newPost: "New post" },
      report: { title: "Report post", reason: "Why are you reporting this?", submit: "Submit report", success: "Report submitted. Thank you." },
      common: { loading: "Loading...", error: "Something went wrong.", page: "Page", of: "of", prev: "Previous", next: "Next", cancel: "Cancel", confirm: "Confirm", save: "Save", close: "Close" },
    },
  },
  ru: {
    translation: {
      appName: "TeachHub",
      tagline: "Интерактивное обучение, готовое к запуску.",
      nav: { feed: "Лента", publish: "Опубликовать", profile: "Профиль", admin: "Админ", login: "Войти", register: "Регистрация", logout: "Выйти", workspace: "Студия" },
      search: { placeholder: "Поиск по названию...", subject: "Предмет", grade: "Класс", type: "Тип", all: "Все", clear: "Сбросить фильтры", results: "постов найдено" },
      subjects: { mathematics: "Математика", physics: "Физика", chemistry: "Химия", literature: "Литература", history: "История", foreign_languages: "Иностранные языки", other: "Другое" },
      grades: { "1-4": "1-4 классы", "5-6": "5-6 классы", "7-8": "7-8 классы", "9-11": "9-11 классы", university: "Университет" },
      types: { html: "Интерактив", worksheet: "Рабочий лист", blog: "Блог", all: "Все типы" },
      card: { views: "просмотров", by: "автор", open: "Открыть", download: "Скачать", readMore: "Читать далее", files: "файлов", draft: "Черновик" },
      feed: { title: "Каталог постов", subtitle: "Просматривайте интерактивные уроки, рабочие листы и блоги учителей — без регистрации.", empty: "Нет постов по вашему запросу.", emptyPublish: "Опубликуйте первый пост!", exploreTab: "Обзор", followingTab: "Подписки", followingEmpty: "Вы пока ни на кого не подписаны. Подпишитесь на учителей, чтобы видеть их посты здесь.", loginForFollowing: "Войдите, чтобы видеть посты учителей, на которых вы подписаны." },
      view: { runIt: "Интерактивный плеер", like: "Нравится", liked: "Нравится", favorite: "В избранное", favorited: "В избранном", report: "Пожаловаться", edit: "Редактировать", delete: "Удалить", back: "Назад к ленте", loginToInteract: "Войдите, чтобы ставить лайки и добавлять в избранное.", deleteConfirm: "Удалить этот пост? Это действие необратимо.", views: "просмотров", published: "Опубликовано", fullscreen: "На весь экран", download: "Скачать", attachments: "Вложения", viewProfile: "Автор" },
      publish: {
        titleNew: "Создать пост", titleEdit: "Редактировать пост", chooseType: "Что вы публикуете?",
        typeHtmlDesc: "Интерактивный HTML, который работает на сайте (тест, игра, визуализация).",
        typeWorksheetDesc: "Файлы для скачивания — изображения и документы (PDF, DOCX, XLSX...).",
        typeBlogDesc: "Пост с текстом и изображениями, чтобы делиться опытом и советами.",
        formTitle: "Название", subject: "Предмет", grade: "Класс", description: "Описание", descHint: "Максимум 500 символов",
        tags: "Теги (через запятую)", html: "HTML-код", htmlHint: "Вставьте интерактивный HTML. Запускается в песочнице. Максимум 1 МБ.",
        blogBody: "Текст поста", blogBodyHint: "Напишите статью. Добавьте изображения ниже.",
        worksheetFiles: "Файлы рабочего листа", worksheetHint: "Загрузите изображения (PNG/JPG/WebP) и документы (PDF, DOCX, XLSX, PPTX). Максимум 25 МБ каждый.",
        blogImages: "Изображения (необязательно)", uploadFile: "Загрузить файл", uploadImage: "Добавить изображение", uploading: "Загрузка...",
        remove: "Удалить", folder: "Папка", noFolder: "Без папки",
        preview: "Предпросмотр", previewEmpty: "Здесь появится предпросмотр.", submit: "Опубликовать", update: "Сохранить",
        cancel: "Отмена", success: "Пост опубликован!", updated: "Пост обновлён!", selectSubject: "Выберите предмет", selectGrade: "Выберите класс",
        draftLabel: "Сохранить как черновик", draftHint: "Черновики видны только вам, пока вы не опубликуете.", saveDraft: "Сохранить черновик",
      },
      auth: { loginTitle: "С возвращением", registerTitle: "Создайте аккаунт преподавателя", email: "Эл. почта", password: "Пароль", confirmPassword: "Подтвердите пароль", passwordMismatch: "Пароли не совпадают", name: "Полное имя", loginBtn: "Войти", registerBtn: "Зарегистрироваться", noAccount: "Нет аккаунта?", haveAccount: "Уже есть аккаунт?", passwordHint: "Минимум 8 символов", loginSuccess: "Вы вошли!", registerSuccess: "Аккаунт создан!", show: "Показать пароль", hide: "Скрыть пароль" },
      profile: { title: "Мой профиль", myTasks: "Мои посты", favorites: "Избранное", settings: "Настройки", followers: "Подписчики", following: "Подписки", noTasks: "Вы ещё ничего не опубликовали.", noFavorites: "Пока нет избранного.", noFollowers: "Пока нет подписчиков.", noFollowing: "Вы пока ни на кого не подписаны.", changeName: "Отображаемое имя", changeEmail: "Эл. почта", saveAccount: "Сохранить", currentPassword: "Текущий пароль", newPassword: "Новый пароль", changePassword: "Сменить пароль", dangerZone: "Опасная зона", deleteAccount: "Удалить аккаунт", deleteConfirm: "Навсегда удалить аккаунт и все ваши посты?", saved: "Сохранено!", passwordChanged: "Пароль изменён!", accountDeleted: "Аккаунт удалён.", openStudio: "Открыть Студию", viewProfile: "Публичный профиль", changeAvatar: "Изменить аватар", bio: "Обо мне", bioHint: "Расскажите немного о себе (до 500 символов)", hideFollowers: "Скрыть список подписчиков", hideFollowing: "Скрыть список подписок", privacy: "Приватность" },
      follow: { follow: "Подписаться", following: "Вы подписаны", unfollow: "Отписаться", followers: "Подписчики", followingList: "Подписки", posts: "постов", memberSince: "С нами с", noPosts: "Пока нет постов." },
      workspace: { title: "Студия", logoHint: "Назад к ленте", account: "Аккаунт", fullscreen: "Полноэкранный предпросмотр", exit: "Выйти из полноэкранного режима", folders: "Папки", allTasks: "Все посты", byType: "По типу", bySubject: "По предмету", myFolders: "Мои папки", createFolder: "Новая папка", folderName: "Название папки", create: "Создать", posts: "Посты", noPosts: "Здесь нет постов.", selectPost: "Выберите пост для предпросмотра", edit: "Редактировать", deleteFolder: "Удалить папку", deleteFolderConfirm: "Удалить эту папку? Посты внутри будут перемещены из папки (не удалены).", newPost: "Новый пост" },
      report: { title: "Пожаловаться на пост", reason: "Почему вы жалуетесь?", submit: "Отправить жалобу", success: "Жалоба отправлена. Спасибо." },
      common: { loading: "Загрузка...", error: "Что-то пошло не так.", page: "Страница", of: "из", prev: "Назад", next: "Далее", cancel: "Отмена", confirm: "Подтвердить", save: "Сохранить", close: "Закрыть" },
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
