#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>

class QStackedWidget;
class ApiClient;
class AuthSession;
class StreamClient;
class LoginWidget;
class RegisterWidget;
class ForgotPasswordWidget;
class ChatWidget;

// Top-level shell: owns the shared ApiClient/AuthSession/StreamClient and
// swaps between the login/register/forgot-password/chat screens the same
// way frontend/src/app/app.routes.ts switches routes.
class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);

private:
    ApiClient *m_api;
    AuthSession *m_auth;
    StreamClient *m_stream;

    QStackedWidget *m_stack;
    LoginWidget *m_loginPage;
    RegisterWidget *m_registerPage;
    ForgotPasswordWidget *m_forgotPasswordPage;
    ChatWidget *m_chatPage;

    void showLogin();
    void showChat();
    void openUserMenu();
    void openAdminMenu();
};
#endif // MAINWINDOW_H
