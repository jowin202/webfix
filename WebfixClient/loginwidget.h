#ifndef LOGINWIDGET_H
#define LOGINWIDGET_H

#include <QWidget>

class ApiClient;
class AuthSession;
class QLineEdit;
class QCheckBox;
class QLabel;
class QPushButton;

// Mirrors frontend/src/app/components/login-window/login-window.component:
// username/password login, guest login (shown only when the server allows
// it), and links into registration / password recovery.
class LoginWidget : public QWidget
{
    Q_OBJECT
public:
    LoginWidget(ApiClient *api, AuthSession *auth, QWidget *parent = nullptr);

    void refreshPublicInfo();

signals:
    void registerRequested();
    void forgotPasswordRequested();

private:
    ApiClient *m_api;
    AuthSession *m_auth;

    QLineEdit *m_username;
    QLineEdit *m_password;
    QCheckBox *m_remember;
    QLabel *m_error;
    QPushButton *m_loginButton;

    QWidget *m_guestBox;
    QLineEdit *m_guestUsername;
    QLabel *m_guestError;
    QPushButton *m_guestLoginButton;

    QLabel *m_onlineCountLabel;

    void doLogin();
    void doGuestLogin();
};

#endif // LOGINWIDGET_H
