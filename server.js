require("dotenv").config();

const express = require("express");
const multer = require("multer");
const cors = require("cors");
const fs = require("fs");

const app = express();

const upload = multer({
    dest: "uploads/"
});

app.use(cors());

app.post("/upload-receipt", upload.single("receipt"), async (req, res) => {

    try {

        console.log("Чек получен!");

        if (!req.file) {
            return res.status(400).json({
                success: false,
                message: "Фотография чека не загружена."
            });
        }

        const imageBuffer = fs.readFileSync(req.file.path);

        const base64Image =
            imageBuffer.toString("base64");

        const mimeType =
            req.file.mimetype || "image/jpeg";

        console.log("Фото подготовлено для DeepSeek!");

        const response = await fetch(
            "https://api.deepseek.com/chat/completions",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization":
                        `Bearer ${process.env.DEEPSEEK_API_KEY}`
                },

                body: JSON.stringify({

                    model:
                        "deepseek-v4-flash-vision-exp",

                    messages: [

                        {
                            role: "user",

                            content: [

                                {
                                    type: "text",

                                    text: `
Это фотография кассового чека.

Распознай информацию на изображении.

Верни данные только в формате JSON.

Используй строго такую структуру:

{
  "shop": "",
  "date": "",
  "total": "",
  "items": [
    {
      "name": "",
      "price": "",
      "category": ""
    }
  ]
}

Правила:

- shop — название магазина или организации.
- date — дата покупки.
- total — итоговая сумма покупки.
- items — список всех товаров или услуг, которые видны на чеке.
- name — название товара или услуги.
- price — цена товара или услуги.
- category — категория товара или услуги.

Для category используй одну из этих категорий:

продукты
кафе и рестораны
транспорт
здоровье
красота
одежда
электроника
дом
развлечения
образование
спорт
путешествия
услуги
другое

Если категорию невозможно определить, используй "другое".

Не придумывай данные, которых нет на фотографии.

Если какое-то поле невозможно прочитать, оставь его пустым.

Обязательно верни валидный JSON без текста до или после JSON.
`
                                },

                                {
                                    type: "image_url",

                                    image_url: {
                                        url:
                                            `data:${mimeType};base64,${base64Image}`
                                    }

                                }

                            ]

                        }

                    ],

                    response_format: {
                        type: "json_object"
                    },

                    thinking: {
                        type: "disabled"
                    },

                    max_tokens: 4000,

                    stream: false

                })

            }
        );


        if (!response.ok) {

            const errorText =
                await response.text();

            console.error(
                "DeepSeek HTTP ошибка:",
                response.status
            );

            console.error(
                "Ответ DeepSeek:",
                errorText
            );

            throw new Error(
                `DeepSeek вернул ошибку ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log("DeepSeek ответил!");


        const result =
            data.choices?.[0]?.message?.content;


        if (!result) {

            throw new Error(
                "DeepSeek не вернул результат."
            );

        }


        console.log(result);


        // Проверяем, что DeepSeek действительно
        // вернул корректный JSON.
        JSON.parse(result);


        res.json({

            success: true,

            message:
                "Чек распознан!",

            result:
                result

        });


    }

    catch (error) {

        console.error(
            "Ошибка:",
            error.message
        );


        res.status(500).json({

            success: false,

            message:
                "Не удалось распознать чек."

        });

    }

    finally {

        // Удаляем временную фотографию
        // после обработки.

        if (
            req.file &&
            fs.existsSync(req.file.path)
        ) {

            fs.unlinkSync(
                req.file.path
            );

        }

    }

});


app.listen(3000, () => {

    console.log(
        "Backend запущен!"
    );

    console.log(
        "Адрес: http://localhost:3000"
    );

});