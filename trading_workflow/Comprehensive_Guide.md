# A Trader's Guide to the Kalshi API: Getting Authorization Right

Let's be real, trading with an API isn't about memorizing a million endpoints. It's about getting one thing right: **Authorization**. Most of the time, this is the part that trips everyone up, especially when you're trying to use AI tools that don't understand the nuance. This guide breaks down how we've solved the hard part so you can focus on the easy part: making trades.

---

## The Hard Part: Nailing Authorization

Why is this so difficult? Because Kalshi (rightfully) needs to be 100% sure that every single request is coming from you. It's not enough to just send an API key. You have to prove it's you *at the exact moment you make the request*.

This is done through a process called **Request Signing**.

Here’s the secret sauce, which is handled entirely by our `clients.py` file so you don't have to worry about it:

1.  **Create a Unique Message:** For every API call, the client creates a unique string of text. It's a simple combination of:
    *   The exact time (down to the millisecond).
    *   The request type (`GET` or `POST`).
    *   The API endpoint path (like `/portfolio/orders`).

    The raw message looks something like this: `1672531200000POST/portfolio/orders`

2.  **Sign It with Your Private Key:** The client then takes this unique message and uses your secret `.pem` file to create a cryptographic signature. This signature is a long, scrambled piece of text that can only be created by your specific private key. It's impossible to fake.

3.  **Send Everything to Kalshi:** The final request sent to Kalshi includes the normal stuff (like the order details) plus three critical security headers:
    *   Your public API Key ID.
    *   The timestamp from step 1.
    *   The unique signature from step 2.

Kalshi's servers perform the same process on their end. If the signature they generate matches the one you sent, they know the request is authentic and from you. If it doesn't, the request is rejected.

**This is the step where most people fail.** Getting the timestamp perfect, formatting the message correctly, and signing it properly is tricky. Our `clients.py` handles this flawlessly every time.

---

## The Easy Part: Making API Calls

Once the authorization is handled by the client, everything else becomes dead simple. You don't need to think about the signing process at all. You just use the endpoints.

Want to place an order? You just tell the client **what** you want to do and **where** you want to do it.

**Instead of this (The Hard Way):**
```
1. Get current time in milliseconds.
2. Format the message string: time + "POST" + "/portfolio/orders".
3. Sign the message with your private key.
4. Base64 encode the signature.
5. Build the request with 3 different security headers.
6. Send the request.
7. Hope you did everything right.
```

**You just do this (The Easy Way, using our scripts):**
```bash
python simple_order.py KXHIGHNY-25JUL20-B87.5 yes buy 1 98
```

The `simple_order.py` script just makes a single, clean call to the client, and the client does all the hard work. This is the power of a well-structured system. It solves the hard problem once so you can focus on your trading strategy.
