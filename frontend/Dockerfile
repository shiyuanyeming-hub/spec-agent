FROM node:20-alpine
WORKDIR /app
# TODO(v0.2): Next.js 前端初始化后补全构建步骤
COPY package.json .
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]
