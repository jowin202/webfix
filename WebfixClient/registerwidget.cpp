#include "registerwidget.h"
#include "apiclient.h"

#include <QVBoxLayout>
#include <QFormLayout>
#include <QLineEdit>
#include <QLabel>
#include <QPushButton>
#include <QJsonObject>

RegisterWidget::RegisterWidget(ApiClient *api, QWidget *parent)
    : QWidget(parent)
    , m_api(api)
{
    auto *root = new QVBoxLayout(this);
    root->setAlignment(Qt::AlignTop);

    auto *title = new QLabel(QStringLiteral("Register"));
    QFont titleFont = title->font();
    titleFont.setPointSize(titleFont.pointSize() + 4);
    titleFont.setBold(true);
    title->setFont(titleFont);
    root->addWidget(title);

    auto *form = new QFormLayout();
    m_username = new QLineEdit();
    m_name = new QLineEdit();
    m_tel = new QLineEdit();
    m_mail = new QLineEdit();
    m_fediverse = new QLineEdit();
    m_password = new QLineEdit();
    m_password->setEchoMode(QLineEdit::Password);
    m_confirmPassword = new QLineEdit();
    m_confirmPassword->setEchoMode(QLineEdit::Password);

    form->addRow(QStringLiteral("Username:"), m_username);
    form->addRow(QStringLiteral("Name:"), m_name);
    form->addRow(QStringLiteral("Phone:"), m_tel);
    form->addRow(QStringLiteral("E-mail:"), m_mail);
    form->addRow(QStringLiteral("Fediverse ID:"), m_fediverse);
    form->addRow(QStringLiteral("Password:"), m_password);
    form->addRow(QStringLiteral("Confirm password:"), m_confirmPassword);
    root->addLayout(form);

    m_message = new QLabel();
    m_message->setWordWrap(true);
    m_message->hide();
    root->addWidget(m_message);

    m_submitButton = new QPushButton(QStringLiteral("Register"));
    root->addWidget(m_submitButton);

    auto *backButton = new QPushButton(QStringLiteral("Back to login"));
    backButton->setFlat(true);
    root->addWidget(backButton);

    connect(m_submitButton, &QPushButton::clicked, this, &RegisterWidget::doRegister);
    connect(backButton, &QPushButton::clicked, this, &RegisterWidget::backToLoginRequested);
}

void RegisterWidget::reset()
{
    m_username->clear();
    m_name->clear();
    m_tel->clear();
    m_mail->clear();
    m_fediverse->clear();
    m_password->clear();
    m_confirmPassword->clear();
    m_message->hide();
}

void RegisterWidget::doRegister()
{
    m_message->hide();

    if (m_username->text().isEmpty() || m_name->text().isEmpty() || m_password->text().isEmpty()) {
        m_message->setStyleSheet("color: red;");
        m_message->setText(QStringLiteral("Username, name and password are required."));
        m_message->show();
        return;
    }
    if (m_password->text() != m_confirmPassword->text()) {
        m_message->setStyleSheet("color: red;");
        m_message->setText(QStringLiteral("Passwords do not match."));
        m_message->show();
        return;
    }

    const QJsonObject body{
        {"username", m_username->text()},
        {"name", m_name->text()},
        {"tel", m_tel->text()},
        {"mail", m_mail->text()},
        {"fediverse_id", m_fediverse->text()},
        {"password", m_password->text()},
        {"verify_mail", true},
        {"verify_fediverse", true},
    };

    m_submitButton->setEnabled(false);
    m_api->postJson("/api/register/register/", QString(), body, [this](const QJsonValue &result, int) {
        m_submitButton->setEnabled(true);
        if (ApiClient::isError(result)) {
            m_message->setStyleSheet("color: red;");
            m_message->setText(result.toObject().value("error_string").toString(QStringLiteral("Registration failed.")));
            m_message->show();
            return;
        }
        m_message->setStyleSheet("color: green;");
        m_message->setText(QStringLiteral("Registration successful. Check your mail/fediverse inbox if account activation is required, then log in."));
        m_message->show();
        m_password->clear();
        m_confirmPassword->clear();
    });
}
