# Company reviews(Recenze-společností)
#### Video Demo: https://youtu.be/vMCfhkx-Wto
#### Description:

This is a relatively simple web app made with Python and Flask. Its' main purpose is to create a space where user reviews of companies can be added and seen. At least where I am from, Czechia, it tends to be relatively hard to find reviews of companies. The reviews that are accessible are usually made, or being allowed to exist, as part of the company's marketing. I would like my users to have access to reviews where the companies do not have many ways to interfer with the content. Generally speaking I would like to be able to see reviews of companies that they, them selves, do not want to be reviewd. That is in my opinion really importand for the consumers to be able to get the info they need before they make the decision to contract with a company. 

## Example usecase
If you live within a small comunity, let's say a small city or a village even, and want to have your bathroom renovated, for example, chances are you will go to seek knowledge from your neighbours, colleagues or other members of your community. They will probably provide you with the knowledge necessary to find the right contractor. Chances are that you will be warned that some particular contractor might not be the best available. Or the really good one might be recommended to you. The bad ones might also not survive in the market for long because people in smaller communities tend to share information more effectively and after a while, everyone will be wary of the bad apple.

However, if you were to live in a big city, or maybe you just moved in and don't know anyone there, the story might be different. When looking for the contractor, there might be noone you can turn to. Or they just might not know. The market in the cities is way larger so there are more contractors in general. Which unfortunately means that there are more bad contractors too. In order to avoid them, you just might benefit from a site like this where reviews of companies are pooled and you can look them up.

# Note:
- The design of this app is by no means perfect. Some functionality would surely be subject to change in case I decided I wanted to publish the application to the world wide web. The following paragraphs describe the the application as it stands at the moment, late august 2024. 
- A lot of the design features were discussed with the cs50 ddb AI and chatGPT.
- The contents of the application are made in Czech language. However, the complete functionality is described in the following text.

## Terms, conditions, privacy, cookies
Policies concerning these topics were not yet formulated as of now. They contain only placeholder text at the moment. If this site were ever to be released, these policies need to be formulated comprehensively in accordance with the law. Which is especially the case, since I, as the author, live within the EU and GDPR and similar regulations apply. At the moment, this is not within my possibilities. The application was therefore configured similarly to the CS50's Finance problem set as per flask configuration concerning cookies etc.

## Functionality
This application has multiple modes of use. If a user does not sign in, he/she has access to the existing reviews. The information about the already registered companies is available to the public. All of the approved reviews as well.

If the user wants to add a new review, or potentially add a new company to the app, a registration and signing in are necessary. Completely anonymous reviews are not allowed. However, usernames can be whatever the user chooses. Emails, that are asociated with the users must be valid existing adresses, since their validity is being checked during registration, but they are not publicly shown on the application interface. 

Lastly, all reviews are subject to being checked by the administrator prior to being published. The administrator also has access to all reviews that have already been allowed to be shown on the page in case he missed something or in case the user changes the contents of the review not in accordance with the terms and conditions. 

## Mode of operation
As described previously, the users have the ability to add companies and reviews within this web app. There are, however, some constraints in place on how this can be done. When a company is added, no action has to be taken by the administrator. The site does not save the information about the user who added the company. When a review is added however, the user id is stored with the review. The review is then saved in a temporary table in the database. It is shown to the administrator of the app in an admin console. The administrator can either approve the review or delete it at this time. When a review is approved it is moved into a public database within the app and is shown to the users. 

A review can later be either edited or deleted. There is a catch however. Since I do not want the companies to have much power over the revies, I have made the application in such a way, that review can only be edited within 3 days of their creation. After that, they can no longer be edited. They can be deleted. But that also works differently than might be expected. 

When a user decides to delete a review, or their entire account for that matter, the functionality is somewhat similar. A review to be deleted looses all of the identifying content that might make it associable with the user who created it. It is associated with an anonymous user profile that has been created especially for this purpose. It is then shown to the admin whose job is to remove any information from the text of the review, that might tie it to the user. When anonymized, it is again published for all users to see but anonymously. 

When a user decides to delete their entire account, the functionality is similar. All of his personal data is deleted, except for the textual content of the reviews. It then follows the same logic as in the previous example. 

# Parts of the application
Bellow, you can find description of each of the important elements of this application and explanation of their functions.
## index
Index constitutes the home page of the application. It is the default gateway to the app and is public. It shows all reviews published up to date ordered by the date and time they were added in reverse order. Therefore the most recent reviews come first. 

It also contains a search bar which based on what you search for either takes you to reviews, if the company you searched for exists, or it redirects you to add a new company, if it does not yet exist. Depending on if you are signed in or not, it might also take you to the log in page, since only registered and logged in users can add companies and reviews.
## Reviews
In reviews you can search for reviews of specific companies as described above. The same search functionality applies. If what you input into the search bar constitutes a partial match with multiple possibilities, you will be shown all of them and can then choose. 

Otherwise you are directly taken to a part of reviews where you, as user, are given an overview of the company, their overall rating, and you can see all reviews that are asociated with that particular company.
## Add a company
Adding a company constitutes of a simple form with five fields. The first three are compulsory and they are: name of the company, the field in which the company operates(this is done via a select menu) and the general location of the company (this is again done using a select menu and the user is given the choice of counties within Czechia). 

The optional fields contain the adress of the company and its' web page. If those are not given by the used, they remain empty by default and the users are given the information that those values were not registered.

From this moment, this company can receive reviews. After adding a company, the user is redirected to adding a review since it seemed reasonable that many users would want to do so.
## Add a review
Adding a review requires selecting a name of an existing company. The search bar is case insensitive but a valid name must be entered in its' entirety. Otherwise the user is redirected to adding a new company first. The search bar is in fact a bootstrap datalist which provides users with existing companies names.

Then a star rating must be added and lastly a textual review. All fields are compulsory.

When a review is added, as discussed earlier, it first has to be approved by the admin before it is shown in the reviews. 

The user is informed about this through emails and through flash messages. The user is also informed he only has three days if he wants to edit the review.
## User account
The user account contains multiple options. Firstly, there is an overview of the information the user has provided during registration. There is his username(which at the moment can't be changed, then there is his email adress)
### Email
The email adress can be changed by the user. If he chooses to do so, he is redirected to another page, where the current email, password and new email and it repetition for confirmation have to be added. If any value is missing or contains unexpected values, an error message is shown.

If everything goes as planned, the users db is updated and the user is informed via flash message and via email messages to both his current and previous email adresses.
### Password
The password can also be changed by the user. The process follows similar steps as the email change and the user is again informed about this via flash and via email.
### Request copy of personal data
Since GDPR requires this functionality it was added. So far it only confirms to the user via email and flash that he has made such a request and it also informs the admin that such a request was made and he should comply. No automatic functionality was yet implemented.
### Account deletion
The user can also choose to delete his account. This functionality was described above. 

The personal info of the user and his association with any of the reviews is deleted, he is informed about this via email, then he is logged out and redirected to the homepage.
The reviews are anonymized and afted admin check are published again anonymously.
### Review edit / delete
within the account, the user is shown all of his reviews. He can choose to delete his asociation with any of them or edit them, if he is within the window when this is allowed.
## Register / Login / Logout
This functionality is implemented in the industry standard way I would say. A user can register on the site, he has to input an email, which serves as his unique identifier as well as the id, a username and a password. At the moment, the password can be anything. The application does not enforce any lenght and/or special characters. That might change in the future.

To log in a valid password and email must be provided.
## Admin access
The admin access console contains multiple elements. The admin's role is to approve or delete new reviews, to anonymize reviews that the users no longer want to be associated with and has access to all existing reviews on the site where he can double check whether they are in compliance with the terms and conditions. 

The last part seems to be most important since at the moment, when a user chooses to edit his review, it does not go through the admin again for approval.

# Aditional addons and technologies used
## bootstrap
https://getbootstrap.com/docs/5.2/getting-started/introduction/
## email-validator
https://pypi.org/project/email-validator/
## Flask-Mail
https://flask-mail.readthedocs.io/en/latest/
## Bcrypt
https://www.geeksforgeeks.org/password-hashing-with-bcrypt-in-flask/
## sqlite3
https://github.com/ghaering/pysqlite/blob/master/doc/sphinx/sqlite3.rst
## cs50
https://pypi.org/project/cs50/