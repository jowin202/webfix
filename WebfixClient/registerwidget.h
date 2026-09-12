#ifndef REGISTERWIDGET_H
#define REGISTERWIDGET_H

#include <QWidget>

class ApiClient;
class QLineEdit;
class QLabel;
class QPushButton;

// Mirrors frontend/src/app/components/register-window/register-window.component:
// POST /api/register/register/ with verify_mail/verify_fediverse hardcoded
// true, same as the Angular client.
class RegisterWidget : public QWidget
{
    Q_OBJECT
public:
    explicit RegisterWidget(ApiClient *api, QWidget *parent = nullptr);

    void reset();

signals:
    void backToLoginRequested();

private:
    ApiClient *m_api;

    QLineEdit *m_username;
    QLineEdit *m_name;
    QLineEdit *m_tel;
    QLineEdit *m_mail;
    QLineEdit *m_fediverse;
    QLineEdit *m_password;
    QLineEdit *m_confirmPassword;
    QLabel *m_message;
    QPushButton *m_submitButton;

    void doRegister();
};

#endif // REGISTERWIDGET_H
