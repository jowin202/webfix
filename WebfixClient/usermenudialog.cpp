#include "usermenudialog.h"
#include "apiclient.h"
#include "authsession.h"

#include <QVBoxLayout>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLineEdit>
#include <QLabel>
#include <QPushButton>
#include <QColorDialog>
#include <QJsonObject>
#include <QGroupBox>

UserMenuDialog::UserMenuDialog(ApiClient *api, AuthSession *auth, QWidget *parent)
    : QDialog(parent)
    , m_api(api)
    , m_auth(auth)
{
    setWindowTitle(QStringLiteral("Profile"));

    auto *root = new QVBoxLayout(this);
    auto *form = new QFormLayout();
    m_name = new QLineEdit();
    m_tel = new QLineEdit();
    m_mail = new QLineEdit();
    m_fediverse = new QLineEdit();
    m_loginMsg = new QLineEdit();
    m_logoutMsg = new QLineEdit();
    m_password = new QLineEdit();
    m_password->setEchoMode(QLineEdit::Password);
    m_password->setPlaceholderText(QStringLiteral("Leave empty to keep current password"));

    form->addRow(QStringLiteral("Name:"), m_name);
    form->addRow(QStringLiteral("Phone:"), m_tel);
    form->addRow(QStringLiteral("E-mail:"), m_mail);
    form->addRow(QStringLiteral("Fediverse ID:"), m_fediverse);
    form->addRow(QStringLiteral("Login message:"), m_loginMsg);
    form->addRow(QStringLiteral("Logout message:"), m_logoutMsg);
    form->addRow(QStringLiteral("New password:"), m_password);
    root->addLayout(form);

    m_message = new QLabel();
    m_message->setWordWrap(true);
    m_message->hide();
    root->addWidget(m_message);

    auto *saveButton = new QPushButton(QStringLiteral("Save"));
    root->addWidget(saveButton);

    auto *colorBox = new QGroupBox(QStringLiteral("Username color gradient"));
    auto *colorLayout = new QHBoxLayout(colorBox);
    m_colorFromButton = new QPushButton();
    m_colorToButton = new QPushButton();
    auto *applyGradientButton = new QPushButton(QStringLiteral("Apply"));
    colorLayout->addWidget(new QLabel(QStringLiteral("From:")));
    colorLayout->addWidget(m_colorFromButton);
    colorLayout->addWidget(new QLabel(QStringLiteral("To:")));
    colorLayout->addWidget(m_colorToButton);
    colorLayout->addWidget(applyGradientButton);
    root->addWidget(colorBox);
    updateColorButton(m_colorFromButton, m_colorFrom);
    updateColorButton(m_colorToButton, m_colorTo);

    auto *closeButton = new QPushButton(QStringLiteral("Close"));
    root->addWidget(closeButton);

    connect(saveButton, &QPushButton::clicked, this, &UserMenuDialog::save);
    connect(applyGradientButton, &QPushButton::clicked, this, &UserMenuDialog::applyGradient);
    connect(closeButton, &QPushButton::clicked, this, &QDialog::accept);
    connect(m_colorFromButton, &QPushButton::clicked, this, [this]() {
        const QColor c = QColorDialog::getColor(m_colorFrom, this);
        if (c.isValid()) {
            m_colorFrom = c;
            updateColorButton(m_colorFromButton, c);
        }
    });
    connect(m_colorToButton, &QPushButton::clicked, this, [this]() {
        const QColor c = QColorDialog::getColor(m_colorTo, this);
        if (c.isValid()) {
            m_colorTo = c;
            updateColorButton(m_colorToButton, c);
        }
    });
}

void UserMenuDialog::updateColorButton(QPushButton *button, const QColor &color) const
{
    button->setStyleSheet(QString("background-color: %1;").arg(color.name()));
    button->setText(color.name());
}

void UserMenuDialog::reload()
{
    m_message->hide();
    m_password->clear();
    m_api->get("/api/data/get_user_info/", m_auth->token, [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result)) {
            return;
        }
        const QJsonObject obj = result.toObject();
        m_name->setText(obj.value("name").toString());
        m_tel->setText(obj.value("tel").toString());
        m_mail->setText(obj.value("mail").toString());
        m_fediverse->setText(obj.value("fediverse_id").toString());
        m_loginMsg->setText(obj.value("login_msg").toString());
        m_logoutMsg->setText(obj.value("logout_msg").toString());
    });
}

void UserMenuDialog::save()
{
    m_message->hide();
    QJsonObject body{
        {"name", m_name->text()},
        {"tel", m_tel->text()},
        {"mail", m_mail->text()},
        {"fediverse_id", m_fediverse->text()},
        {"login_msg", m_loginMsg->text()},
        {"logout_msg", m_logoutMsg->text()},
    };
    if (!m_password->text().isEmpty()) {
        body["password"] = m_password->text();
    }

    m_api->postJson("/api/data/set_user_info/", m_auth->token, body, [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result)) {
            m_message->setStyleSheet("color: red;");
            m_message->setText(result.toObject().value("error_string").toString(QStringLiteral("Save failed.")));
            m_message->show();
            return;
        }
        m_message->setStyleSheet("color: green;");
        m_message->setText(QStringLiteral("Saved."));
        m_message->show();
        m_password->clear();
    });
}

void UserMenuDialog::applyGradient()
{
    const QString fromHex = m_colorFrom.name().mid(1); // strip '#'
    const QString toHex = m_colorTo.name().mid(1);
    m_api->postJson(QString("/api/data/change_name_color/%1/%2/").arg(fromHex, toHex), m_auth->token, QJsonObject(),
                     [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result)) {
            m_message->setStyleSheet("color: red;");
            m_message->setText(QStringLiteral("Could not apply color gradient."));
            m_message->show();
            return;
        }
        m_message->setStyleSheet("color: green;");
        m_message->setText(QStringLiteral("Color gradient applied."));
        m_message->show();
    });
}
