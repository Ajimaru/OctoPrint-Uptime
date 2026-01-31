module.exports = [
  {
    extends: ["@eslint/js/recommended"],
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "module",
    },
    rules: {
      "no-console": "off",
    },
  },
];
