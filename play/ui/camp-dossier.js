/* «Штабной стол» (концепт Б): карточка жителя — личное дело на бумажном бланке, раздел «Работы» —
   чертежи построек. Только оформление поверх штатных разделов лагеря: кнопки, приказы, экономика
   и сохранения остаются в обработчиках игры (game.camp.assign и др. вызываются штатными кнопками).
   Подключается из camp-navigation.js; опирается на window.terraCampUI (camp-mobile.js).
   Иконки — из набора игры (game-icons.net, CC BY 3.0: Lorc, Delapouite и др., см. README). */
(() => {
  'use strict';
  const PATHS = {
    wood: 'M353.86 48.45c-10.626-.16-20.45 3.456-29.14 13.253l-.193.217-50.586 50.098.628.703c3.395 3.7 3.106 9.463-.642 12.804-3.748 3.342-9.505 2.97-12.793-.825l-5.985-6.712a36.232 36.232 0 0 1-2.544 3.178c-5.116 5.68-11.746 9.448-18.688 11.023l5.438 20.302c2.54 8.98-8.582 15.417-15.102 8.738l-41.2 40.803a73.33 73.33 0 0 1 4.26-.135c40.63 0 73.616 33.616 73.616 74.672 0 .803-.036 1.598-.06 2.395l141.94-153.74c8.252-10.316 9.687-20.888 6.985-31.832C407.08 82.4 399.6 71.29 389.653 62.967a67.967 67.967 0 0 0-9.835-6.854L258.56 182.725c-3.418 3.685-9.193 3.856-12.824.38-3.63-3.478-3.71-9.255-.175-12.83l115.932-121.05a45.56 45.56 0 0 0-5.494-.694 48.013 48.013 0 0 0-2.137-.08zM232.31 85.597c-4.224-.048-8.876 1.842-12.583 5.96-6.327 7.024-5.918 16.11-.913 20.62 5.006 4.508 14.088 3.968 20.415-3.057 6.325-7.024 5.917-16.112.91-20.62-1.877-1.69-4.328-2.672-6.992-2.867-.277-.02-.556-.032-.837-.035zm-27.95 63.94c-7.19-.12-13.63 2.222-19.577 8.925l-.19.217-99.734 98.77c10.89.53 20.967 4.222 29.386 10.167a74.889 74.889 0 0 1 11.785-32.332l.44-.67 6.39-8.21a74.532 74.532 0 0 1 6.11-6.05l70.907-70.224a31.108 31.108 0 0 0-4.07-.534c-.486-.03-.968-.05-1.448-.057zm193.3 14.415a45.862 45.862 0 0 0-6.588.52L245.744 321.88a74.987 74.987 0 0 1-9.976 10.806l-5.715 6.19a80.074 80.074 0 0 1 27.34 11.628c-.004-.254-.02-.505-.02-.76 0-12.38 4.545-23.756 12.03-32.496l-.087-.086 1.358-1.344a49.89 49.89 0 0 1 3.16-3.13L381.01 206.545c8.52-9.363 20.055-13.314 30.816-12.662 10.908.66 21.093 5.423 29.33 12.316 8.238 6.892 14.684 16.035 17.278 26.538a37.756 37.756 0 0 1 1.078 9.922c4.62-9.422 4.9-19.095 2.242-28.918-3.484-12.87-12.614-25.674-24.47-34.967v.002c-11.194-8.77-24.658-14.314-37.27-14.79-.79-.028-1.573-.04-2.354-.034zm11.926 47.852c-5.712-.106-10.696 1.69-15.463 7.064l-.193.216-82.07 81.28c22.277 2.517 40.072 20.28 43.12 42.585l82.31-89.153c4.454-5.58 5.124-10.833 3.665-16.742-1.468-5.945-5.675-12.3-11.35-17.05-5.678-4.75-12.668-7.778-18.867-8.153-.387-.024-.77-.04-1.152-.047zm-222.274 8.097c-4.898 0-9.644.647-14.167 1.85a45.276 45.276 0 0 1 5.994-.41c24.715 0 45.067 19.99 45.067 44.566 0 24.576-20.355 44.567-45.068 44.567-24.718 0-45.07-19.992-45.07-44.567 0-2.83.282-5.593.797-8.277a57.873 57.873 0 0 0-3.166 18.94c0 31.482 24.873 56.668 55.613 56.668s55.61-25.185 55.61-56.668c0-31.482-24.87-56.668-55.61-56.668zm-8.173 19.44c-15.12 0-27.07 11.857-27.07 26.566 0 14.71 11.945 26.567 27.07 26.567 15.117 0 27.067-11.858 27.067-26.567 0-14.71-11.944-26.566-27.068-26.566zm-3.388 7.357c8.742 0 16.023 7.276 16.023 16.02s-7.285 16.02-16.023 16.02c-8.742 0-16.025-7.275-16.025-16.02 0-8.743 7.287-16.02 16.025-16.02zm-93.61 28.68c-21.25 0-38.427 17.364-38.427 39.2 0 21.835 17.177 39.2 38.426 39.2 21.25 0 38.426-17.364 38.426-39.2 0-3.01-.338-5.933-.957-8.74a74.367 74.367 0 0 1-3.08-8.838c-6.297-12.877-19.314-21.623-34.39-21.623zm-.36 11.016c15.59 0 27.085 14.1 27.085 29.823 0 15.724-11.498 29.82-27.086 29.82-15.59 0-27.087-14.098-27.087-29.82 0-15.727 11.5-29.824 27.088-29.824zm372.58.325c-6.907-.118-13.068 2.118-18.79 8.567l-.193.22-96.345 95.415c27.285 1.628 49.25 23.576 51.547 50.926l96.64-104.672c5.384-6.735 6.24-13.283 4.48-20.42a29.402 29.402 0 0 0-.868-2.844l-63.383 66.342c-3.41 3.703-9.196 3.888-12.837.41-3.64-3.48-3.72-9.267-.175-12.844l65.103-68.144a9.1 9.1 0 0 1 1.122-1.018 46.184 46.184 0 0 0-2.447-2.203c-6.715-5.62-14.988-9.227-22.463-9.68-.467-.028-.93-.046-1.39-.054zm-372.9 14.73c-7.59 0-13.74 7.046-13.74 15.738 0 8.69 6.15 15.736 13.74 15.736s13.743-7.045 13.743-15.736c0-8.69-6.152-15.737-13.742-15.737zm224.952 16.6c-17.17 0-31.04 14.004-31.04 31.694 0 17.69 13.87 31.695 31.04 31.695s31.04-14.006 31.04-31.696-13.87-31.693-31.04-31.693zm-2.285 11.155c11.398 0 19.28 10.28 19.28 21.092 0 10.814-7.884 21.09-19.28 21.09-11.4 0-19.282-10.277-19.282-21.09 0-10.814 7.883-21.092 19.28-21.092zm-163.378 5.13-14.027 15.192a57.675 57.675 0 0 1-7.235 7.838l-3.986 4.317c9.624 5.793 17.842 13.746 24.006 23.185 6.715-14.72 17.602-27.106 31.113-35.588-11.134-2.634-21.307-7.826-29.87-14.946zm72.31 20.704c-34.83 0-63.015 28.553-63.015 64.192 0 35.64 28.186 64.194 63.016 64.194s63.017-28.554 63.017-64.194c0-35.638-28.188-64.193-63.017-64.193zM68.68 370.114C42.442 374.65 22.5 397.775 22.5 425.96c0 14.03 4.95 26.802 13.146 36.66a48.17 48.17 0 0 1-8.064-26.725v-.004c-.005-26.31 21.188-47.994 47.29-47.994 26.105 0 47.298 21.684 47.292 47.996.005 20.913-13.386 38.89-31.986 45.393 22.622-5.065 40.05-24.075 43.076-47.908a83.297 83.297 0 0 1-1.207-14.145c0-2.07.077-4.125.226-6.16-4.7-20.763-20.513-37.028-40.71-42.11-3.065.528-6.21.817-9.422.817-4.64 0-9.146-.586-13.462-1.665zm140.48.643c27.187 0 49.2 22.702 49.2 50.203 0 27.503-22.016 50.204-49.2 50.204-27.187 0-49.2-22.702-49.2-50.203 0-27.5 22.017-50.202 49.2-50.202zm0 17.998c-17.21 0-31.2 14.195-31.2 32.205 0 18.012 13.983 32.206 31.2 32.206 17.212 0 31.2-14.195 31.2-32.205 0-18.01-13.982-32.204-31.2-32.204zm81.856 8.148a82.57 82.57 0 0 1 2.642 13.912 55.86 55.86 0 0 1 12.852-11.38 1.475 1.475 0 0 1-.094.003c-5.38 0-10.554-.9-15.4-2.536zm-216.14 8.992c-16.2 0-29.295 13.238-29.29 29.995v.005c-.005 16.756 13.09 29.994 29.29 29.994 16.197 0 29.295-13.24 29.29-29.995v-.004c.005-16.756-13.093-29.994-29.29-29.994zm133.706.256c8.967 0 14.96 7.945 14.96 15.953 0 8.01-5.993 15.952-14.96 15.952-8.966 0-14.96-7.943-14.96-15.952 0-8.008 5.994-15.953 14.96-15.953zm127.203 2.664c-20.47 0-37.013 16.723-37.013 37.766 0 21.042 16.544 37.766 37.013 37.766 20.47 0 37.012-16.723 37.012-37.766 0-21.042-16.543-37.766-37.012-37.766zM71.833 422.39c8.965 0 14.958 7.943 14.958 15.952 0 8.01-5.992 15.953-14.958 15.953-8.966 0-14.96-7.944-14.96-15.953 0-8.01 5.994-15.953 14.96-15.953zm267.923 1.423c14.727 0 26.683 12.307 26.683 27.037 0 14.73-11.958 27.037-26.684 27.037-14.728 0-26.682-12.308-26.682-27.037 0-14.73 11.955-27.038 26.682-27.038zm0 18c-4.802 0-8.682 3.845-8.682 9.037s3.877 9.037 8.682 9.037c4.8 0 8.683-3.846 8.683-9.037 0-5.193-3.88-9.038-8.684-9.038z',
    scrap: 'M179.625 22.313 163.22 58.937a87.676 87.676 0 0 0-9.72-.624c-10.577-.066-20.857 1.808-30.47 5.28L99.78 31.032 55.75 63.188l24.063 33.657a87.946 87.946 0 0 0-14.5 35.75l-42.72 4.687 5.345 54.25 45.468-5A89.896 89.896 0 0 0 94 213.502l-19.406 43.375 49.375 22.094 19.5-43.564c11.656 1.242 23.08.128 33.75-3l28.124 38.53 31.72-23.186 11.655 20.156A209.02 209.02 0 0 0 209.624 307l-49.22-28.344-25.718 46.72 48.125 27.937a206.71 206.71 0 0 0-14.343 53.812H112.5v53.72h56.22a204.365 204.365 0 0 0 8.03 35.06h169.312c-23.915-10.758-40.562-34.788-40.562-62.717 0-37.964 30.754-68.75 68.72-68.75 37.963 0 68.75 30.786 68.75 68.75 0 27.93-16.67 51.96-40.595 62.718h91.5V200.375l-11.688-6.406L454.594 242A204.25 204.25 0 0 0 401 227.28v-55.53h-53.72v55.47c-18.303 2.377-35.83 7.183-52.31 14.03l-27.126-47.28-36 20.25-9.25-12.97a88.715 88.715 0 0 0 15.5-31.72l44.437-4.843-5.342-54.25-42.25 4.157A89.013 89.013 0 0 0 212.376 81.5L229 44.406l-49.375-22.093zm-27.344 84.25c23.3-.24 42.94 17.827 44.376 41.343 1.48 24.275-17.004 45.144-41.28 46.625-24.278 1.483-45.145-16.974-46.626-41.25-1.48-24.274 16.973-45.142 41.25-46.624.76-.046 1.53-.086 2.28-.094z',
    food: 'M440.156 98.063c-4.05-.11-8.044 1.117-11.656 4-1.542 1.23-3.1 2.884-4.47 4.75-22.9 31.22-48.278 57.33-75.186 81-8.76 14.692 10.695 44.406 25.594 44.406 34.144-12.928 69.617-22.516 106.75-26.314 42.628-4.358 17.688-68.134-26.25-45.47 30.3-22.666 7.094-61.79-14.782-62.374zM310.47 108.156c-6.167-.108-12.215 1.172-17.595 4.28a30.82 30.82 0 0 0-4.406 3.095c-.038-.056-.09-.13-.126-.186-79.912 66.402-116.334 73.468-158.22 86.844-6.886 2.2-12.27 7.18-16.5 15.5s-6.892 19.843-7.343 33.125c-.9 26.563 6.935 59.927 23.72 89.03 16.72 28.99 43.37 53.946 67.656 67.126 12.143 6.59 23.682 10.167 32.375 10.436 8.694.27 13.915-1.95 17.782-7.375 30.986-43.45 89.343-69.052 156.157-92.25-.005-.006.003-.023 0-.03a31.008 31.008 0 0 0 5.842-2.594c8.2-4.738 13.535-12.897 16.282-22.125 2.747-9.227 3.22-19.75 2.03-31.25-.953-9.233-3.033-19.127-6.155-29.374-5.916 1.366-11.628 3.157-17.908 5.47 2.835 9.25 4.69 17.978 5.5 25.81 1.007 9.74.403 18.06-1.375 24.033-1.777 5.972-4.412 9.338-7.718 11.25-3.308 1.91-7.543 2.505-13.595 1.06-6.052-1.443-13.55-5.07-21.47-10.81-15.838-11.482-33.334-31.223-47.624-56-14.29-24.78-22.61-49.838-24.624-69.314-1.006-9.738-.403-18.027 1.375-24 1.78-5.973 4.414-9.37 7.72-11.28 1.653-.957 3.52-1.58 5.75-1.782.557-.05 1.147-.067 1.75-.063 1.81.014 3.824.272 6.094.814 6.05 1.444 13.518 5.04 21.437 10.78 8.218 5.957 16.884 14.166 25.314 24.126 5.07-4.055 9.34-8.25 13.406-13.188-8.97-10.46-18.366-19.26-27.75-26.062-9.354-6.78-18.733-11.61-28.094-13.844a46.242 46.242 0 0 0-7.03-1.125 43.882 43.882 0 0 0-2.657-.124zm7.967 34.188c-.438.024-.86.063-1.28.125-17.327 2.54-14.97 36.035 5.03 74.56 20 38.528 50.52 67.576 67.844 65.032 5.995-.88 9.263-5.687 10.658-12.875-1.67 2.187-3.847 3.484-6.72 3.907-15.316 2.248-42.316-23.093-60-57.156-17.682-34.064-19.254-63.91-3.937-66.157 3.638-.53 7.69.417 12.345 2.782-8.68-6.8-17.353-10.583-23.938-10.218zM102 325.124c-16.555 1.844-35.304 3.26-57.063 4.376-49.128 2.523-25.555 71.576 30.094 52.22-49.365 29.9 3.86 86.927 26.97 46.75 10.362-18.016 21.88-33.79 34.375-47.814-8.42-9.644-16.078-20.224-22.563-31.47a200.715 200.715 0 0 1-11.812-24.06z',
    water: 'M406.043 316c24.11 96.443-50.59 180-150 180s-174.405-82.38-150-180c15-60 90-150 150-300 60 150 135 240 150 300z',
    chem: 'M433.814 68.664c-2.74.05-5.495.423-8.242 1.152-8.47 2.25-15.3 7.512-20.44 14.49C292.905 120.865 186.494 154.58 75.276 190.4c-39.714 12.79-64.6 51.163-53.006 86.784 11.597 35.62 54.342 52.277 94.035 39.277l-.002.002c109.41-35.827 214.424-69.036 325.12-104.656.56.212 1.13.39 1.694.58-2.62 2.935-4.226 6.796-4.226 11.04 0 9.164 7.43 16.593 16.594 16.593 9.165 0 16.596-7.43 16.596-16.593 0-4.32-1.664-8.24-4.367-11.192 12.75-4.865 21.353-16.866 25.535-30.898 4.547-15.257 4.504-33.654-.584-52.48-5.088-18.828-14.327-34.77-25.94-45.712-8.712-8.206-19.263-13.79-30.175-14.43-.91-.052-1.822-.07-2.736-.054zm.497 18.68a17.2 17.2 0 0 1 1.377.035c5.567.358 11.818 3.34 18.22 9.37 8.535 8.04 16.44 21.165 20.716 36.986 3.622 13.4 4 26.397 2.012 36.852h-52.783c-3.517-6.207-6.512-13.352-8.622-21.158-4.276-15.822-4.046-31.094-.716-42.266 3.33-11.172 9.122-17.497 15.855-19.285a16.148 16.148 0 0 1 3.94-.536zm-38.414 17.043c-3.815 14.734-3.516 32.133 1.29 49.92a114.327 114.327 0 0 0 5.728 16.26h-151.22c-64.405 20.742-125.856 40.507-163.35 52.59-23.24 7.486-35.353 27.407-30.406 42.593 4.946 15.188 26.582 24.333 49.75 16.75 66.89-21.89 199.01-64.39 302.822-97.803 3.76 5.807 7.998 10.967 12.62 15.323.066.06.135.118.2.18-104.876 33.753-241.66 77.74-309.83 100.05-30.827 10.09-64.424-1.334-73.344-28.72-8.92-27.385 11.603-56.22 42.438-66.155 68.055-21.93 208.2-66.996 313.302-100.988zm59.58 180.205c-16.948 63.255-40.507 54.472-40.507 91.5 0 22.36 18.146 40.508 40.507 40.508 22.36 0 40.507-18.147 40.507-40.508 0-39.97-23.256-27.12-40.507-91.5z',
    cloth: 'M165.446 34.793c-23.17.023-45.634 12.97-54.612 36.323l-83.67 326.167c-12.673 94.537 81.04 88.742 137.957 65.396 81.422-33.396 181.723-29.213 263.244-8.26l6.45-17.218c-7.38-2.638-15.334-5.988-22.252-8.039.473-4.364.955-8.72 1.437-13.074l23.038 4.118 3.234-18.1c-8.074-1.441-16.147-2.885-24.221-4.328a4816.63 4816.63 0 0 1 1.87-16.189l22.134 3.278 2.693-18.186c-7.548-1.12-15.098-2.238-22.647-3.355.456-3.765.91-7.53 1.375-11.29 7.615 1.092 15.231 2.183 22.847 3.273l2.607-18.2-23.164-3.316c.46-3.593 1.29-9.988 1.76-13.577l22.781 2.55 2.045-17.57a56812.69 56812.69 0 0 1-22.402-2.508c.783-5.767 1.917-11.182 2.728-16.943 7.67 1.12 15.341 2.244 23.012 3.368l2.31-17.139c-7.683-1.127-15.366-2.25-23.05-3.374.792-5.415 1.252-10.129 2.071-15.542 7.074 1.264 14.149 2.528 21.223 3.79l3.232-18.1-21.654-3.866c.736-4.676 1.473-9.35 2.23-14.026 6.978 1.673 13.955 3.347 20.932 5.022L465.276 208c-7.401-1.778-14.803-3.554-22.204-5.33a2809.25 2809.25 0 0 1 2.132-12.477c6.98 1.583 13.961 3.165 20.942 4.746l4.064-17.93c-7.271-1.65-14.543-3.298-21.815-4.946.769-4.267 1.55-8.535 2.342-12.805l20.742 5.151 4.431-17.843-21.751-5.405c.741-3.847 1.494-7.696 2.254-11.548l20.28 5.014 4.413-17.849-21.057-5.207a2444.47 2444.47 0 0 1 2.571-12.374c8.386 2.41 13.13 2.364 21.41 4.99L486 88.456c-83.808-26.776-179.25-33.22-244.192-6.453-24.337 114.036-37.305 221.4-68.032 338.64-3.407 13-14.47 21.89-27.342 28.064-27 11.608-64.033 13.778-84.63-4.91-10.971-10.34-16.174-27.036-12.467-47.579 2.303-12.762 10.883-21.986 20.834-26.378 19.749-7.074 43.492-4.25 58.893 7.95 12.463 9.302 12.318 38.283-3.882 31.82-9.639-6.17-1.964-11.851-8.615-17.378-11.6-7.428-26.42-10.872-38.972-5.57-5.564 2.455-8.887 5.737-10.166 12.822-2.94 16.29.685 24.996 6.985 30.933 18.333 13.49 45.279 10.495 64.068 1.712 10.045-4.82 16.277-11.436 17.511-16.147 30.538-116.518 43.443-224.123 68.293-339.964-11.796-28.344-35.67-41.247-58.84-41.225z',
    heart: 'M372.48 31.215c-77.65 0-116.48 65.73-116.48 65.73s-38.83-65.72-116.48-65.72c-37.14 0-107.77 33.72-107.77 125.13 0 161.24 224.25 324.43 224.25 324.43s224.25-163.19 224.25-324.43c0-91.42-70.63-125.13-107.77-125.14zm-145.492 115.02h60.698v79.415h79.238v60.7h-79.238v79.884h-60.698V286.35h-80.064v-60.7h80.064z',
    info: 'M256 21C126.426 21 21 126.426 21 256s105.426 235 235 235 235-105.426 235-235S385.574 21 256 21zm0 36c110.118 0 199 88.882 199 199s-88.882 199-199 199S57 366.118 57 256 145.882 57 256 57zm-7.352 36.744c-8.227 0-15.317 2.976-21.27 8.928-5.776 5.952-8.665 12.955-8.665 21.008 0 8.227 2.89 15.23 8.666 21.006 5.95 5.776 13.04 8.666 21.268 8.666 8.228 0 15.23-2.89 21.006-8.666 5.777-5.777 8.666-12.78 8.666-21.006 0-8.053-2.976-15.056-8.927-21.008-5.777-5.952-12.692-8.928-20.745-8.928zm-62.757 82.453v28.096h46.215v186.13H185.89v27.833h140.22v-27.834h-45.69V176.197h-94.53z',
    lock: 'M254.28 17.313c-81.048 0-146.624 65.484-146.624 146.406V236h49.594v-69.094c0-53.658 43.47-97.187 97.03-97.187 53.563 0 97.032 44.744 97.032 97.186V236h49.594v-72.28c0-78.856-65.717-146.407-146.625-146.407zM85.157 254.688c-14.61 22.827-22.844 49.148-22.844 76.78 0 88.358 84.97 161.5 191.97 161.5 106.998 0 191.968-73.142 191.968-161.5 0-27.635-8.26-53.95-22.875-76.78H85.155zM254 278.625c22.34 0 40.875 17.94 40.875 40.28 0 16.756-10.6 31.23-25.125 37.376l32.72 98.126h-96.376l32.125-98.125c-14.526-6.145-24.532-20.62-24.532-37.374 0-22.338 17.972-40.28 40.312-40.28z',
    shield: 'M256 16c25 24 100 72 150 72v96c0 96-75 240-150 312-75-72-150-216-150-312V88c50 0 125-48 150-72z',
    check: 'M17.47 250.9C88.82 328.1 158 397.6 224.5 485.5c72.3-143.8 146.3-288.1 268.4-444.37L460 26.06C356.9 135.4 276.8 238.9 207.2 361.9c-48.4-43.6-126.62-105.3-174.38-137z',
    moon: 'M253.125 18.563c-131.53 0-238.375 106.813-238.375 238.343 0 131.53 106.846 238.344 238.375 238.344 131.53 0 238.344-106.815 238.344-238.344 0-131.528-106.816-238.344-238.345-238.344zm-23.938 52.093c40.517 0 77.988 12.904 108.532 34.813a154.099 154.099 0 0 0-17.064-.97c-84.157 0-152.375 68.25-152.375 152.406 0 84.157 68.22 152.375 152.376 152.375 5.762 0 11.467-.313 17.063-.936-30.545 21.91-68.016 34.812-108.533 34.812-102.98 0-186.28-83.272-186.28-186.25 0-102.977 83.3-186.25 186.28-186.25z',
    rest: 'M100 384h312v48H100zM96 320h320v48H96zM140 260c20-80 64-120 116-120s96 40 116 120zM330 65h65v25l-37 45h37v25h-75v-25l37-45h-27z',
    person: 'M250.882 22.802c-23.366 3.035-44.553 30.444-44.553 65.935 0 19.558 6.771 36.856 16.695 48.815l11.84 14.263-18.217 3.424c-12.9 2.425-22.358 9.24-30.443 20.336-8.085 11.097-14.266 26.558-18.598 44.375-7.843 32.28-9.568 71.693-9.842 106.436h42.868l11.771 157.836c29.894 6.748 61.811 6.51 90.602.025l10.414-157.86h40.816c-.027-35.169-.477-75.126-7.584-107.65-3.918-17.934-9.858-33.372-18.04-44.343-8.185-10.97-18.08-17.745-32.563-19.989l-18.592-2.88 11.736-14.704c9.495-11.897 15.932-28.997 15.932-48.082 0-37.838-23.655-65.844-49.399-65.844z',
    // Свои знаки: у генератора и мастерской в игре одна иконка «молоток».
    bolt: 'M300 24 112 292h112L168 488 400 216H276L300 24z',
    anvil: 'M48 128h416v64H336v40h80v56H224v-56h48v-40H48v-64zm80 208h256v48H128v-48z',
  };
  const icon = name => PATHS[name] ? `<svg class="gi" viewBox="0 0 512 512" aria-hidden="true"><path d="${PATHS[name]}"/></svg>` : '';
  // Скрепка — собственный SVG.
  const CLIP = '<svg class="dossierClip" viewBox="0 0 24 64" aria-hidden="true"><path d="M8 50V12a5 5 0 0 1 10 0v40a8 8 0 0 1-16 0V16" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>';
  const RES = [['wood', 'Дерево'], ['scrap', 'Лом'], ['food', 'Еда'], ['water', 'Вода'], ['chem', 'Химикаты'], ['cloth', 'Ткань']];
  const RES_KEY = {'дерево': 'wood', 'лом': 'scrap', 'металлолом': 'scrap', 'еда': 'food', 'тушёнка': 'food', 'вода': 'water', 'химикаты': 'chem', 'ткань': 'cloth'};
  const NEEDS = [['Мораль', 'heart'], ['Еда', 'food'], ['Вода', 'water'], ['Отдых', 'rest'], ['Безопасность', 'shield']];
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  function start(tries = 0) {
    const panel = document.getElementById('campPanel');
    const body = panel?.querySelector('#campBody');
    if (!panel || !body || !window.terraCampUI) { if (tries < 100) setTimeout(() => start(tries + 1), 100); return; }
    const ui = window.terraCampUI;
    const camp = () => window.game?.p?.camp;
    const tab = () => window.game?.ui?.campPanel?.tab || null;
    let listOrder = [];

    function infoButton(label, onTap) {
      const b = el('button', 'deskInfo');
      b.type = 'button';
      b.innerHTML = '<i aria-hidden="true">i</i>';
      b.setAttribute('aria-label', label);
      b.title = label;
      b.addEventListener('click', event => { event.stopPropagation(); onTap(); });
      return b;
    }
    function openSheet(title, content) {
      const sheet = ui.openInfo(title, content);
      sheet?.classList.add('deskSheet');
    }

    /* ---------- личное дело жителя ---------- */
    function residentId(root) {
      return root.querySelector('[data-resident-biography]')?.dataset.residentBiography
        || root.querySelector('[data-companion-control]')?.closest('.campResidents')?.querySelector('[data-resident-order]')?.dataset.residentOrder || null;
    }
    function meters(root) {
      const out = {};
      for (const m of root.querySelectorAll('.campFold .campMeter[aria-label]')) {
        const match = /^(.+?):\s*(\d+)\s+из\s+(\d+)/.exec(m.getAttribute('aria-label'));
        if (match) out[match[1]] = {value: +match[2], max: +match[3]};
      }
      return out;
    }
    function step(root, id, delta) {
      const ids = listOrder.length ? listOrder : Object.keys(camp()?.settlers || {});
      const i = ids.indexOf(id);
      if (i < 0 || ids.length < 2) return;
      const next = ids[(i + delta + ids.length) % ids.length];
      // Штатный путь: «К жителям» → карточка следующего жителя.
      root.querySelector('[data-camp-back="list"]')?.click();
      const open = () => {
        const target = body.querySelector(`[data-resident="${CSS.escape(next)}"]`);
        if (target) { target.click(); body.scrollTop = 0; return true; }
        return false;
      };
      if (!open()) setTimeout(open, 0);
    }
    function dossier(root) {
      const id = residentId(root);
      const settler = id ? camp()?.settlers?.[id] : null;
      root.classList.add('dossier');
      const head = root.querySelector(':scope > .residentIdentityHead');
      const info = head?.querySelector('.residentIdentityInfo');
      const ids = Object.keys(camp()?.settlers || {});
      if (info && !info.querySelector('.dossierNo')) {
        info.prepend(el('small', 'dossierNo', `Личное дело № ${String(Math.max(1, ids.indexOf(id) + 1)).padStart(2, '0')}`));
        head.querySelector('.residentPortrait')?.insertAdjacentHTML('afterbegin', CLIP);
      }
      // Штамп состояния — из штатной строки «Статус: …».
      const live = root.querySelector(':scope > .residentLiveStatus');
      const statusText = (live?.textContent || '').replace(/^\s*Статус:\s*/i, '').trim();
      let stamp = head?.querySelector('.dossierStamp');
      if (head && statusText) {
        if (!stamp) { stamp = el('span', 'dossierStamp'); head.append(stamp); }
        if (stamp.textContent !== statusText) stamp.textContent = statusText;
        stamp.dataset.tone = settler?.status === 'working' ? 'ok' : settler?.status === 'idle' ? 'idle' : 'warn';
      }
      // Потребности: иконка + штриховая шкала, числа без подписей (подписи — в aria-label).
      const m = meters(root);
      let needs = root.querySelector(':scope > .dossierNeeds');
      if (!needs) { needs = el('div', 'dossierNeeds'); needs.setAttribute('role', 'list'); head?.after(needs); }
      const sig = NEEDS.map(([k]) => m[k]?.value ?? '').join('|');
      if (needs.dataset.sig !== sig) {
        needs.dataset.sig = sig;
        needs.replaceChildren(...NEEDS.filter(([k]) => m[k]).map(([k, ico]) => {
          const v = m[k], ratio = Math.max(0, Math.min(1, v.value / (v.max || 100)));
          const row = el('div', 'dossierNeed');
          row.setAttribute('role', 'listitem');
          row.setAttribute('aria-label', `${k}: ${v.value} из ${v.max}`);
          row.dataset.level = ratio < .35 ? 'bad' : ratio < .6 ? 'warn' : 'ok';
          row.style.setProperty('--v', ratio.toFixed(3));
          const short = k === 'Безопасность' ? 'Защита' : k;
          row.innerHTML = `${icon(ico)}<span class="dossierNeedName">${short}</span><span class="dossierBar"><i></i></span><b>${v.value}</b>`;
          row.title = k;
          return row;
        }));
      }
      // «i» — история, навыки, снаряжение и черты (копии штатных блоков, только чтение).
      if (head && !head.querySelector(':scope > .deskInfo')) {
        const name = head.querySelector('h3')?.textContent || 'Личное дело';
        head.append(infoButton('Подробности: история, навыки, снаряжение', () => {
          const box = el('div', 'dossierDetails');
          const bio = root.querySelector('.residentBio');
          if (bio) for (const p of bio.querySelectorAll('p, small')) box.append(p.cloneNode(true));
          const fold = root.querySelector('.campFold');
          if (fold) { const f = fold.cloneNode(true); f.open = true; f.querySelector('summary')?.remove(); box.append(el('h4', '', 'Навыки и снаряжение'), ...f.childNodes); }
          openSheet(name, box);
        }));
      }
      // Наряд на работу: печати; текущая — обведена.
      const jobs = root.querySelector(':scope > .campJobs');
      if (jobs) {
        for (const b of jobs.querySelectorAll('[data-resident-job]')) {
          const opt = b.closest('.residentJobOption') || b.parentElement;
          const on = !!settler && b.dataset.residentJob === settler.job;
          opt.classList.toggle('isCurrent', on);
          if (on) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
          let lock = opt.querySelector(':scope > .dossierLock');
          if (b.disabled && !lock) { lock = el('span', 'dossierLock'); lock.innerHTML = icon('lock'); opt.append(lock); }
          else if (!b.disabled && lock) lock.remove();
        }
      }
      const h3 = root.querySelector(':scope > h3');
      if (h3 && !h3.dataset.dossier) { h3.dataset.dossier = '1'; h3.classList.add('dossierOrderTitle'); }
      // Рация: предыдущий / следующий житель.
      let radio = root.querySelector(':scope > .dossierRadio');
      if (!radio && id) {
        radio = el('nav', 'dossierRadio');
        radio.setAttribute('aria-label', 'Листать личные дела');
        const prev = el('button', 'dossierStep', 'Пред.');
        prev.type = 'button'; prev.dataset.step = '-1'; prev.setAttribute('aria-label', 'Предыдущий житель');
        const next = el('button', 'dossierStep', 'След.');
        next.type = 'button'; next.dataset.step = '1'; next.setAttribute('aria-label', 'Следующий житель');
        const dial = el('output', 'dossierDial');
        radio.append(prev, dial, next);
        radio.addEventListener('click', e => { const s = e.target.closest('[data-step]'); if (s) step(root, id, +s.dataset.step); });
        root.append(radio);
      }
      if (radio) {
        const order = listOrder.length ? listOrder : ids;
        const n = order.length, i = order.indexOf(id);
        const t = i >= 0 ? `жилец ${i + 1} из ${n}` : `жителей: ${n}`;
        const dial = radio.querySelector('.dossierDial');
        if (dial.textContent !== t) dial.textContent = t;
        for (const b of radio.querySelectorAll('button')) b.disabled = n < 2;
      }
    }

    /* ---------- чертежи построек ---------- */
    function costChips(text, res) {
      const wrap = el('div', 'bpCost');
      for (const part of text.replace(/^\s*Цена:\s*/i, '').split('·')) {
        const m = /^\s*([^:]+):\s*(\d+)/.exec(part);
        if (!m) continue;
        const key = RES_KEY[m[1].trim().toLowerCase()];
        const need = +m[2], have = key ? Math.floor(res?.[key] ?? 0) : null;
        const chip = el('span', 'bpChip');
        chip.innerHTML = (key ? icon(key) : '') + `<b>${need}</b>`;
        chip.setAttribute('aria-label', `${m[1].trim()}: ${need}${have != null ? `, есть ${have}` : ''}`);
        chip.title = m[1].trim();
        if (have != null && have < need) chip.dataset.lack = '1';
        wrap.append(chip);
      }
      return wrap;
    }
    function blueprints() {
      const root = body.firstElementChild;
      if (!root) return;
      root.classList.add('blueprints');
      const res = camp()?.res || {};
      // Бирки ресурсов сверху.
      let tags = root.querySelector(':scope > .deskTags');
      if (!tags) { tags = el('div', 'deskTags'); tags.setAttribute('role', 'list'); tags.setAttribute('aria-label', 'Запасы лагеря'); root.prepend(tags); }
      const sig = RES.map(([k]) => Math.floor(res[k] ?? 0)).join('|');
      if (tags.dataset.sig !== sig) {
        tags.dataset.sig = sig;
        tags.replaceChildren(...RES.map(([k, label]) => {
          const t = el('span', 'deskTag');
          t.setAttribute('role', 'listitem');
          const v = Math.floor(res[k] ?? 0);
          t.setAttribute('aria-label', `${label}: ${v}`);
          t.title = label;
          t.innerHTML = `${icon(k)}<small>${label}</small><b>${v ? v : 'нет'}</b>`;
          if (!v) t.dataset.empty = '1';
          return t;
        }));
      }
      // Записка снабжения: длинная подсказка уходит под «i».
      const supply = root.querySelector(':scope > .campConstructionSupply');
      const hint = supply?.querySelector(':scope > small:not(.campReason)');
      if (hint && !supply.querySelector(':scope > .deskInfo')) {
        hint.classList.add('deskHint');
        const title = supply.querySelector(':scope > strong')?.textContent || 'Снабжение стройки';
        supply.append(infoButton(`Подробности: ${title}`, () => openSheet(title, el('p', '', hint.textContent))));
      }
      let n = 0;
      for (const card of root.querySelectorAll('.campCard[data-building]')) {
        n++;
        card.classList.add('bp');
        const mark = {generator: 'bolt', workshop: 'anvil'}[card.dataset.building];
        if (mark && card.dataset.mark !== mark) {
          card.dataset.mark = mark;
          const glyph = card.querySelector(':scope > .campIcon');
          if (glyph) glyph.innerHTML = icon(mark);
        }
        const smalls = [...card.querySelectorAll(':scope > small')];
        const button = card.querySelector(':scope > button.campButton');
        const levelText = smalls[0]?.textContent || '';
        const costEl = smalls.find(s => /^\s*Цена:/i.test(s.textContent));
        const reasonEl = smalls.find(s => s.classList.contains('campReason'));
        for (const s of smalls) s.classList.add('bpNote');
        if (!card.querySelector(':scope > .bpNo')) {
          const name = card.querySelector(':scope > strong')?.textContent || 'Постройка';
          card.prepend(el('small', 'bpNo', `Чертёж № ${String(n).padStart(2, '0')}`));
          card.append(infoButton(`Подробности: ${name}`, () => {
            const box = el('div', 'bpDetails');
            for (const s of card.querySelectorAll(':scope > small.bpNote')) box.append(el('p', '', s.textContent.replace(/^🔒\s*/, '')));
            openSheet(name, box);
          }));
        }
        const level = /Уровень\s+(\d+)/i.exec(levelText);
        let lv = card.querySelector(':scope > .bpLevel');
        if (level) {
          if (!lv) { lv = el('span', 'bpLevel'); card.querySelector(':scope > strong')?.after(lv); }
          if (lv.textContent !== `ур. ${level[1]}`) lv.textContent = `ур. ${level[1]}`;
        }
        const costSig = `${costEl?.textContent || ''}|${sig}`;
        if (card.dataset.costSig !== costSig || !card.querySelector(':scope > .bpCost') === !!costEl) {
          card.dataset.costSig = costSig;
          card.querySelector(':scope > .bpCost')?.remove();
          if (costEl) (button || card.lastElementChild).before(costChips(costEl.textContent, res));
        }
        const reason = (reasonEl?.textContent || '').replace(/^🔒\s*/, '');
        const lack = card.querySelector('.bpChip[data-lack]');
        const state = button && !button.disabled ? 'ok' : (!/уров/i.test(reason) && (lack || /ресурс/i.test(reason))) ? 'lack' : 'locked';
        let stamp = card.querySelector(':scope > .bpStamp');
        if (!stamp) { stamp = el('span', 'bpStamp'); card.append(stamp); }
        if (stamp.dataset.tone !== state) {
          stamp.dataset.tone = state;
          stamp.textContent = state === 'ok' ? 'Хватает' : state === 'lack' ? 'Не хватает' : 'Закрыто';
        }
        if (stamp.title !== (reason || stamp.textContent)) stamp.title = reason || stamp.textContent;
      }
    }

    /* ---------- общий цикл ---------- */
    let queued = false;
    const observer = new MutationObserver(() => schedule());
    function decorate() {
      queued = false;
      observer.disconnect();
      try {
        const t = panel.classList.contains('hidden') ? null : tab();
        const residents = body.querySelector(':scope > .campResidents');
        const card = t === 'settlers' && residents?.querySelector(':scope > .residentIdentityHead') ? residents : null;
        // Native resident navigation reuses this root for the list and task
        // targets. Dossier styles hide folds that the list needs for hiring.
        residents?.classList.toggle('dossier', !!card);
        body.classList.toggle('deskDossier', !!card);
        body.classList.toggle('deskBuild', t === 'build');
        if (t === 'settlers' && residents && !card) {
          listOrder = [...residents.querySelectorAll('[data-resident]')].filter(e => e.getClientRects().length).map(e => e.dataset.resident);
        }
        if (card) dossier(card);
        if (t === 'build') blueprints();
      } catch (error) { console.error('[Terra camp dossier]', error); }
      observer.takeRecords();
      observer.observe(body, {childList: true, subtree: true});
    }
    function schedule() { if (!queued) { queued = true; queueMicrotask(decorate); } }
    panel.addEventListener('terra:camp-tab', schedule);
    panel.addEventListener('terra:camp-refresh', schedule);
    new MutationObserver(schedule).observe(panel, {attributes: true, attributeFilter: ['class']});
    decorate();
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', () => start(), {once: true});
})();
